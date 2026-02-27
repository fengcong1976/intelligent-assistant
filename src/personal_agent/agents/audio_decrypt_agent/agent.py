"""
NCM音频解密智能体 - 解密网易云音乐.ncm文件并转为MP3格式
"""
import os
import shutil
import struct
from pathlib import Path
from typing import Dict, Any, Optional, List

from loguru import logger

from ..base import BaseAgent, Task, TaskStatus


class AudioDecryptAgent(BaseAgent):
    """NCM音频解密智能体"""
    
    supported_file_types = [".ncm", ".qmc", ".kwm"]
    
    CORE_KEY = bytearray([0x68, 0x7A, 0x48, 0x52, 0x41, 0x6D, 0x73, 0x6F,
                          0x35, 0x6B, 0x49, 0x6E, 0x62, 0x61, 0x78, 0x57])
    
    def __init__(self):
        super().__init__(
            name="audio_decrypt_agent",
            description="NCM音频解密智能体 - 解密网易云音乐.ncm文件并转为MP3格式"
        )
        self.register_capability("decrypt_ncm", "解密NCM文件")
        self.register_capability("batch_decrypt", "批量解密")
        self.register_file_formats(open_formats=[".ncm", ".qmc", ".kwm"])
        
        project_root = Path(__file__).parent.parent.parent
        self.cache_dir = project_root / "data" / "ncm_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("🔓 NCM解密智能体已初始化")
    
    async def execute_task(self, task: Task) -> Any:
        """执行解密任务"""
        task_type = task.type
        action = task.params.get("action", "decrypt_ncm")
        
        if task_type == "batch_decrypt" or action == "batch_decrypt":
            return await self.batch_decrypt(task)
        elif task_type == "decrypt_ncm" or action == "decrypt_ncm":
            return await self.decrypt_ncm(task)
        elif task_type == "agent_help":
            return self._get_help_info()
        else:
            return {"success": False, "error": f"未知操作: {task_type}"}
    
    async def decrypt_ncm(self, task: Task) -> Dict[str, Any]:
        """解密单个NCM文件"""
        error_msg = task.params.get("error", "")
        if error_msg:
            return {"success": False, "error": error_msg}
        
        file_path = task.params.get("file_path", "")
        
        if not file_path:
            return {"success": False, "error": "未指定文件路径"}
        
        file_path = Path(file_path)
        if not file_path.exists():
            return {"success": False, "error": f"文件不存在: {file_path}"}
        
        if file_path.suffix.lower() != ".ncm":
            return {"success": False, "error": f"不支持的文件格式: {file_path.suffix}"}
        
        try:
            cached_file = self._get_cached_file(str(file_path))
            if cached_file:
                final_path = self._move_to_original_dir(cached_file, file_path.parent)
                return {
                    "success": True,
                    "input": str(file_path),
                    "output": final_path,
                    "cached": True,
                    "message": f"✅ 解密成功！\n📁 输出文件: {final_path}"
                }
            
            output_path = self._decrypt_ncm(str(file_path))
            
            if output_path:
                final_path = self._move_to_original_dir(output_path, file_path.parent)
                logger.info(f"✅ NCM解密成功: {file_path.name} -> {Path(final_path).name}")
                return {
                    "success": True,
                    "input": str(file_path),
                    "output": final_path,
                    "message": f"✅ 解密成功！\n📁 输出文件: {final_path}"
                }
            elif task_type == "agent_help":
                return self._get_help_info()
            else:
                return {"success": False, "error": "解密失败"}
            
        except Exception as e:
            logger.error(f"NCM解密异常: {e}")
            return {"success": False, "error": str(e)}
    
    async def batch_decrypt(self, task: Task) -> Dict[str, Any]:
        """批量解密NCM文件"""
        files = task.params.get("files", [])
        
        if not files:
            return {"success": False, "error": "未指定文件列表"}
        
        results = []
        success_count = 0
        fail_count = 0
        output_files = []
        
        for file_path in files:
            file_path = Path(file_path)
            if not file_path.exists():
                results.append({"file": str(file_path), "success": False, "error": "文件不存在"})
                fail_count += 1
                continue
            
            try:
                cached_file = self._get_cached_file(str(file_path))
                if cached_file:
                    final_path = self._move_to_original_dir(cached_file, file_path.parent)
                    results.append({"file": str(file_path), "success": True, "output": final_path})
                    output_files.append(final_path)
                    success_count += 1
                    continue
                
                output_path = self._decrypt_ncm(str(file_path))
                if output_path:
                    final_path = self._move_to_original_dir(output_path, file_path.parent)
                    results.append({"file": str(file_path), "success": True, "output": final_path})
                    output_files.append(final_path)
                    success_count += 1
                else:
                    results.append({"file": str(file_path), "success": False, "error": "解密失败"})
                    fail_count += 1
            except Exception as e:
                results.append({"file": str(file_path), "success": False, "error": str(e)})
                fail_count += 1
        
        logger.info(f"📊 批量解密完成: 成功 {success_count}, 失败 {fail_count}")
        
        return {
            "success": True,
            "total": len(files),
            "success_count": success_count,
            "fail_count": fail_count,
            "results": results,
            "output_files": output_files,
            "message": f"✅ 批量解密完成！成功 {success_count} 个\n📁 输出文件:\n" + "\n".join(output_files)
        }
    
    def _get_cached_file(self, ncm_path: str) -> Optional[str]:
        """获取已缓存的解密文件"""
        ncm_name = Path(ncm_path).stem
        
        for ext in ['.mp3', '.flac', '.wav', '.m4a', '.ogg']:
            cached = self.cache_dir / (ncm_name + ext)
            if cached.exists():
                return str(cached)
        
        return None
    
    def _move_to_original_dir(self, cached_path: str, original_dir: Path) -> str:
        """将解密后的文件移动到原文件目录"""
        cached_file = Path(cached_path)
        final_path = original_dir / cached_file.name
        
        if final_path.exists():
            logger.info(f"目标文件已存在，跳过移动: {final_path}")
            return str(final_path)
        
        try:
            shutil.move(str(cached_file), str(final_path))
            logger.info(f"📁 文件已移动: {cached_file} -> {final_path}")
            return str(final_path)
        except Exception as e:
            logger.error(f"移动文件失败: {e}")
            return cached_path
    
    def _decrypt_ncm(self, ncm_path: str) -> Optional[str]:
        """解密NCM文件到缓存目录"""
        import json
        import base64
        from Crypto.Cipher import AES
        
        try:
            with open(ncm_path, 'rb') as f:
                header = f.read(8)
                if header != b'CTENFDAM':
                    logger.error(f"无效的 NCM 文件头: {header}")
                    return None
                
                f.seek(2, 1)
                
                key_data_len = struct.unpack('<I', f.read(4))[0]
                key_data = f.read(key_data_len)
                
                key_data = bytearray(key_data)
                for i in range(len(key_data)):
                    key_data[i] ^= 0x64
                
                cipher = AES.new(bytes(self.CORE_KEY), AES.MODE_ECB)
                decrypted_key = cipher.decrypt(bytes(key_data))
                
                key = decrypted_key[17:]
                padding_len = key[-1]
                if padding_len <= len(key) and padding_len <= 16:
                    key = key[:-padding_len]
                
                key_box = self._build_key_box(key)
                
                meta_len = struct.unpack('<I', f.read(4))[0]
                output_format = '.mp3'
                if meta_len > 0:
                    meta_data = f.read(meta_len)
                    try:
                        meta_data = bytearray(meta_data)
                        for i in range(len(meta_data)):
                            meta_data[i] ^= 0x63
                        
                        meta_data = base64.b64decode(meta_data[22:])
                        
                        META_KEY = bytearray([0x23, 0x31, 0x34, 0x6C, 0x6A, 0x6B, 0x5F, 0x21,
                                              0x5C, 0x5D, 0x26, 0x30, 0x55, 0x3C, 0x27, 0x28])
                        cipher = AES.new(bytes(META_KEY), AES.MODE_ECB)
                        decrypted_meta = cipher.decrypt(meta_data)
                        
                        padding_len = decrypted_meta[-1]
                        decrypted_meta = decrypted_meta[:-padding_len]
                        
                        meta = json.loads(decrypted_meta.decode('utf-8'))
                        if 'format' in meta:
                            fmt = meta['format'].lower()
                            if fmt in ['mp3', 'flac', 'wav', 'm4a', 'ogg']:
                                output_format = f'.{fmt}'
                    except Exception as e:
                        logger.debug(f"元数据解析失败: {e}")
                
                f.seek(9, 1)
                
                image_size = struct.unpack('<I', f.read(4))[0]
                if image_size > 0:
                    f.seek(image_size, 1)
                
                output_name = Path(ncm_path).stem + output_format
                output_path = self.cache_dir / output_name
                
                with open(output_path, 'wb') as out:
                    while True:
                        chunk = f.read(0x8000)
                        if not chunk:
                            break
                        
                        chunk = bytearray(chunk)
                        for i in range(len(chunk)):
                            j = (i + 1) & 0xff
                            chunk[i] ^= key_box[(key_box[j] + key_box[(key_box[j] + j) & 0xff]) & 0xff]
                        
                        out.write(chunk)
                
                logger.info(f"✅ NCM 解密成功: {output_path}")
                return str(output_path)
                
        except Exception as e:
            logger.error(f"NCM 解密失败: {e}")
            return None
    
    def _build_key_box(self, key: bytes) -> bytearray:
        """构建密钥盒"""
        box = bytearray(256)
        for i in range(256):
            box[i] = i
        
        j = 0
        key_len = len(key)
        for i in range(256):
            j = (j + box[i] + key[i % key_len]) & 0xff
            box[i], box[j] = box[j], box[i]
        
        return box
    
    def can_handle_file(self, file_path: str, action: str = None) -> bool:
        """检查是否能处理该文件"""
        ext = Path(file_path).suffix.lower()
        return ext in self.supported_file_types
    
    def get_help(self) -> str:
        """获取帮助信息"""
        return """
🔓 NCM音频解密智能体

功能：
• 解密网易云音乐.ncm文件
• 转换为标准MP3/FLAC格式
• 支持批量解密
• 输出到原文件同目录

使用示例：
• "把这个ncm文件转成mp3"
• "解密这个ncm文件"
• "批量解密这些ncm文件"

支持格式：
• .ncm (网易云音乐)
"""
    def _get_help_info(self) -> str:
        """获取帮助信息"""
        return """## 音频解密智能体

### 功能说明
音频解密智能体可以解密网易云音乐等加密音频文件。

### 支持的操作
- **解密文件**：解密单个音频文件
- **批量解密**：批量解密音频文件

### 使用示例
- "解密NCM文件" - 解密单个文件
- "批量解密音频" - 批量解密

### 注意事项
- 支持.ncm等加密格式
- 解密后的文件为MP3格式
- 请确保有合法的使用权限"""
