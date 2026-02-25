"""
NCM 解密模块 - 支持网易云音乐加密格式
参考: https://github.com/anonymous5l/ncmdump
"""
import os
import struct
import threading
from pathlib import Path
from typing import Optional, Callable
from loguru import logger


class NCMDecryptor:
    """NCM 文件解密器"""
    
    CORE_KEY = bytearray([0x68, 0x7A, 0x48, 0x52, 0x41, 0x6D, 0x73, 0x6F,
                          0x35, 0x6B, 0x49, 0x6E, 0x62, 0x61, 0x78, 0x57])
    
    META_KEY = bytearray([0x23, 0x31, 0x34, 0x6C, 0x6A, 0x6B, 0x5F, 0x21,
                          0x5C, 0x5D, 0x26, 0x30, 0x55, 0x3C, 0x27, 0x28])
    
    def __init__(self, cache_dir: str = None):
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            from ..config import settings
            project_root = Path(__file__).parent.parent.parent
            self.cache_dir = project_root / "data" / "ncm_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"NCM 缓存目录: {self.cache_dir}")
        self._decrypting = set()
        self._lock = threading.Lock()
    
    def is_ncm_file(self, file_path: str) -> bool:
        """检查是否为 NCM 文件"""
        return file_path.lower().endswith('.ncm')
    
    def is_decrypting(self, ncm_path: str) -> bool:
        """检查文件是否正在解密"""
        with self._lock:
            return ncm_path in self._decrypting
    
    def decrypt(self, ncm_path: str) -> Optional[str]:
        """解密 NCM 文件（同步）"""
        try:
            with open(ncm_path, 'rb') as f:
                header = f.read(8)
                if header != b'CTENFDAM':
                    logger.error(f"无效的 NCM 文件头: {header}")
                    return None
                
                f.seek(2, 1)
                
                key_data_len = struct.unpack('<I', f.read(4))[0]
                key_data = f.read(key_data_len)
                
                key = self._decrypt_key(key_data)
                if not key:
                    logger.error("密钥解密失败")
                    return None
                
                key_box = self._build_key_box(key)
                
                meta_len = struct.unpack('<I', f.read(4))[0]
                meta = {}
                if meta_len > 0:
                    meta_data = f.read(meta_len)
                    meta = self._decrypt_meta(meta_data)
                
                # 跳过 CRC (4字节) + unknown (5字节) = 9 字节
                f.seek(9, 1)
                
                image_size = struct.unpack('<I', f.read(4))[0]
                if image_size > 0:
                    f.seek(image_size, 1)
                
                output_format = self._get_format_from_meta(meta)
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
    
    def decrypt_async(self, ncm_path: str, callback: Callable[[Optional[str]], None] = None) -> threading.Thread:
        """
        异步解密 NCM 文件
        
        Args:
            ncm_path: NCM 文件路径
            callback: 解密完成回调函数，参数为解密后的文件路径（失败为 None）
            
        Returns:
            解密线程
        """
        def _decrypt_thread():
            with self._lock:
                if ncm_path in self._decrypting:
                    logger.info(f"NCM 文件正在解密中: {ncm_path}")
                    return
                self._decrypting.add(ncm_path)
            
            try:
                result = self.decrypt(ncm_path)
                if callback:
                    callback(result)
            finally:
                with self._lock:
                    self._decrypting.discard(ncm_path)
        
        thread = threading.Thread(target=_decrypt_thread, daemon=True, name=f"NCM-Decrypt-{Path(ncm_path).stem}")
        thread.start()
        return thread
    
    def _decrypt_key(self, key_data: bytes) -> Optional[bytes]:
        """解密密钥数据"""
        try:
            from Crypto.Cipher import AES
            
            key_data = bytearray(key_data)
            for i in range(len(key_data)):
                key_data[i] ^= 0x64
            
            cipher = AES.new(bytes(self.CORE_KEY), AES.MODE_ECB)
            decrypted = cipher.decrypt(bytes(key_data))
            
            key = decrypted[17:]
            
            padding_len = key[-1]
            if padding_len <= len(key) and padding_len <= 16:
                key = key[:-padding_len]
            
            return key
            
        except Exception as e:
            logger.error(f"密钥解密失败: {e}")
            return None
    
    def _decrypt_meta(self, meta_data: bytes) -> dict:
        """解密元数据"""
        import json
        try:
            from Crypto.Cipher import AES
            
            meta_data = bytearray(meta_data)
            for i in range(len(meta_data)):
                meta_data[i] ^= 0x63
            
            import base64
            meta_data = base64.b64decode(meta_data[22:])
            
            cipher = AES.new(bytes(self.META_KEY), AES.MODE_ECB)
            decrypted = cipher.decrypt(meta_data)
            
            padding_len = decrypted[-1]
            decrypted = decrypted[:-padding_len]
            
            return json.loads(decrypted.decode('utf-8'))
        except Exception as e:
            logger.debug(f"元数据解密失败: {e}")
            return {}
    
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
    
    def _get_format_from_meta(self, meta: dict) -> str:
        """从元数据获取输出格式"""
        if meta:
            if 'format' in meta:
                fmt = meta['format'].lower()
                if fmt in ['mp3', 'flac', 'wav', 'm4a', 'ogg']:
                    return f'.{fmt}'
            if 'bitrate' in meta and meta['bitrate'] > 320000:
                return '.flac'
        return '.mp3'
    
    def get_cached_file(self, ncm_path: str) -> Optional[str]:
        """获取已缓存的解密文件"""
        ncm_name = Path(ncm_path).stem
        
        for ext in ['.mp3', '.flac', '.wav', '.m4a', '.ogg']:
            cached = self.cache_dir / (ncm_name + ext)
            if cached.exists():
                return str(cached)
        
        return None


_ncm_decryptor = None


def get_ncm_decryptor() -> NCMDecryptor:
    """获取 NCM 解密器实例"""
    global _ncm_decryptor
    if _ncm_decryptor is None:
        _ncm_decryptor = NCMDecryptor()
    return _ncm_decryptor


def decrypt_ncm(ncm_path: str) -> Optional[str]:
    """解密 NCM 文件（同步）"""
    decryptor = get_ncm_decryptor()
    
    cached = decryptor.get_cached_file(ncm_path)
    if cached:
        logger.info(f"📦 使用缓存的解密文件: {cached}")
        return cached
    
    return decryptor.decrypt(ncm_path)


def decrypt_ncm_async(ncm_path: str, callback: Callable[[Optional[str]], None] = None) -> threading.Thread:
    """
    异步解密 NCM 文件
    
    Args:
        ncm_path: NCM 文件路径
        callback: 解密完成回调函数
        
    Returns:
        解密线程
    """
    decryptor = get_ncm_decryptor()
    
    cached = decryptor.get_cached_file(ncm_path)
    if cached:
        logger.info(f"📦 使用缓存的解密文件: {cached}")
        if callback:
            callback(cached)
        return None
    
    return decryptor.decrypt_async(ncm_path, callback)


def is_ncm_file(file_path: str) -> bool:
    """检查是否为 NCM 文件"""
    return file_path.lower().endswith('.ncm')


def get_cached_ncm(ncm_path: str) -> Optional[str]:
    """获取已缓存的解密文件"""
    return get_ncm_decryptor().get_cached_file(ncm_path)
