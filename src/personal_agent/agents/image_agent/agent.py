"""
Image Agent - 图片生成智能体
使用阿里云通义万相(Wanx)API实现文生图功能
"""
import asyncio
import base64
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime

from loguru import logger

from ..base import BaseAgent, Task
from ...config import settings


class ImageAgent(BaseAgent):
    """图片生成智能体 - 使用阿里云通义万相API"""
    
    PRIORITY = 5
    KEYWORD_MAPPINGS = {
        "生成图片": ("generate", {}),
        "画一张图": ("generate", {}),
        "画图": ("generate", {}),
        "画一幅画": ("generate", {}),
        "创作图片": ("generate", {}),
        "创建图片": ("generate", {}),
        "AI绘画": ("generate", {}),
        "AI画图": ("generate", {}),
        "文生图": ("generate", {}),
        "文字生成图片": ("generate", {}),
        "生成一张图片": ("generate", {}),
        "帮我画": ("generate", {}),
    }

    def __init__(self):
        super().__init__(
            name="image_agent",
            description="图片生成智能体 - 使用AI生成图片"
        )
        
        self.register_capability(
            capability="generate_image",
            description="使用AI生成图片。当用户要求生成图片、画图、AI绘画时调用此工具。",
            parameters={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "图片描述，如'天安门'、'一只可爱的猫咪'、'夕阳下的海滩'"
                    },
                    "size": {
                        "type": "string",
                        "description": "图片分辨率，如'1024*1024'、'1920*1080'、'1080*1920'。默认为'1024*1024'"
                    },
                    "style": {
                        "type": "string",
                        "description": "图片风格，如'3d-cartoon'、'anime'、'oil-painting'等。默认为'<auto>'"
                    },
                    "n": {
                        "type": "integer",
                        "description": "生成图片数量，默认为1"
                    }
                },
                "required": ["prompt"]
            },
            category="image"
        )
        
        self.register_capability("text_to_image", "文本转图片")
        self.register_capability("image_generation", "图片生成")
        
        self._api_key = None
        self._init_api()

    def _init_api(self):
        """初始化API配置"""
        self._api_key = settings.llm.dashscope_api_key
        if not self._api_key:
            logger.warning("⚠️ DashScope API Key 未配置，图片生成功能不可用")

    def _get_save_dir(self) -> Path:
        """获取图片保存目录"""
        try:
            pictures_dir = settings.directory.get_pictures_dir()
            save_dir = pictures_dir / "AI_Generated"
        except Exception:
            save_dir = Path.home() / "Pictures" / "AI_Generated"
        
        save_dir.mkdir(parents=True, exist_ok=True)
        return save_dir

    def _normalize_size(self, size: str) -> str:
        """规范化分辨率到支持的格式"""
        # 通义万相支持的分辨率格式
        SUPPORTED_SIZES = [
            "1024*1024",  # 方形
            "720*1280",   # 纵向 (9:16)
            "1280*720"    # 横向 (16:9)
        ]
        
        # 将 x 替换为 *
        size = size.replace("x", "*")
        
        # 如果已经是支持的格式，直接返回
        if size in SUPPORTED_SIZES:
            return size
        
        # 尝试解析宽高
        try:
            width, height = size.split("*")
            width = int(width)
            height = int(height)
            
            # 根据宽高比选择最接近的分辨率
            if width == height:
                # 方形
                return "1024*1024"
            elif width > height:
                # 横向 (16:9)
                return "1280*720"
            else:
                # 纵向 (9:16)
                return "720*1280"
        except Exception as e:
            # 解析失败，使用默认值
            logger.warning(f"⚠️ 无法解析分辨率 '{size}'，使用默认值: {e}")
            return "1024*1024"
    
    async def execute_task(self, task: Task) -> str:
        """执行图片生成任务"""
        try:
            action = task.params.get("action", "") or task.type
            if action in ["generate_image", "generate", "text_to_image", "image_generation"]:
                action = "generate"
            
            if action == "generate":
                return await self._generate_image(task)
            else:
                return self.cannot_handle(f"未知操作: {action}")
        except Exception as e:
            error_msg = f"❌ 执行任务失败: {str(e)}"
            logger.error(error_msg)
            logger.exception("详细错误信息:")
            return error_msg

    async def _generate_image(self, task: Task) -> str:
        """生成图片"""
        prompt = task.params.get("prompt", "") or task.content
        
        if not prompt:
            return "❌ 请描述您想要生成的图片内容"
        
        if not self._api_key:
            return "❌ DashScope API Key 未配置，请先在设置中配置 DASHSCOPE_API_KEY"
        
        size = task.params.get("size", "1024*1024")
        style = task.params.get("style", "<auto>")
        n = task.params.get("n", 1)
        
        # 转换分辨率格式：将 x 替换为 *
        size = size.replace("x", "*")
        
        # 验证并映射分辨率到支持的格式
        size = self._normalize_size(size)
        
        logger.info(f"🎨 开始生成图片: {prompt[:50]}...")
        logger.info(f"📐 图片参数: size={size}, style={style}, n={n}")
        
        try:
            result = await self._call_wanx_api(prompt, size, style, n)
            
            if result.get("success"):
                images = result.get("images", [])
                if images:
                    return self._format_success_response(prompt, images)
                else:
                    return "❌ 图片生成失败：未返回图片数据"
            else:
                error_msg = result.get("error", "未知错误")
                return f"❌ 图片生成失败：{error_msg}"
                
        except Exception as e:
            logger.error(f"图片生成异常: {e}")
            return f"❌ 图片生成出错：{str(e)}"

    async def _call_wanx_api(
        self, 
        prompt: str, 
        size: str = "1024*1024",
        style: str = "<auto>",
        n: int = 1
    ) -> Dict[str, Any]:
        """调用通义万相API"""
        try:
            import dashscope
            from dashscope import ImageSynthesis
            
            dashscope.api_key = self._api_key
            
            model = "wanx-v1"
            
            def sync_call():
                try:
                    response = ImageSynthesis.call(
                        model=model,
                        prompt=prompt,
                        size=size,
                        style=style,
                        n=n
                    )
                    return response
                except Exception as e:
                    logger.error(f"API调用异常: {e}")
                    return None
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, sync_call)
            
            if response is None:
                return {"success": False, "error": "API调用失败"}
            
            if response.status_code == 200:
                logger.info(f"✅ API 调用成功，状态码: {response.status_code}")
                images = []
                output = response.output
                
                logger.info(f"📦 API 返回的 output 类型: {type(output)}")
                logger.info(f"📦 API 返回的 output 内容: {output}")
                
                if output and hasattr(output, 'results'):
                    results = output.results
                    logger.info(f"📊 API 返回 {len(results)} 个结果")
                    
                    for i, result in enumerate(results):
                        image_url = result.url if hasattr(result, 'url') else None
                        logger.debug(f"🔗 图片 {i}: URL={image_url}")
                        
                        if image_url:
                            saved_path = await self._save_image_from_url(image_url, prompt, i)
                            if saved_path:
                                images.append({
                                    "url": image_url,
                                    "local_path": str(saved_path)
                                })
                            else:
                                logger.warning(f"⚠️ 图片 {i} 下载失败")
                        else:
                            logger.warning(f"⚠️ 结果 {i} 没有 URL 属性")
                else:
                    logger.warning(f"⚠️ output 为空或没有 results 属性: output={output}")
                
                if not images:
                    logger.error(f"❌ 没有成功保存任何图片")
                
                return {"success": True, "images": images}
            else:
                error_msg = response.message if hasattr(response, 'message') else "未知错误"
                code = response.code if hasattr(response, 'code') else "UNKNOWN"
                logger.error(f"API返回错误: {code} - {error_msg}")
                
                if code == "DataInspectionFailed":
                    return {"success": False, "error": "内容审核未通过，请尝试更换描述词，避免敏感内容"}
                
                return {"success": False, "error": f"{error_msg} (代码: {code})"}
                
        except ImportError:
            return {"success": False, "error": "请安装 dashscope: pip install dashscope"}
        except Exception as e:
            logger.error(f"调用Wanx API失败: {e}")
            return {"success": False, "error": str(e)}

    async def _save_image_from_url(self, url: str, prompt: str, index: int) -> Optional[Path]:
        """从URL下载并保存图片"""
        import httpx
        
        try:
            save_dir = self._get_save_dir()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_prompt = "".join(c for c in prompt[:20] if c.isalnum() or c in " _-")
            filename = f"{timestamp}_{safe_prompt}_{index}.png"
            filepath = save_dir / filename
            
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    filepath.write_bytes(response.content)
                    logger.info(f"✅ 图片已保存: {filepath}")
                    return filepath
                else:
                    logger.error(f"下载图片失败: HTTP {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"保存图片失败: {e}")
            return None

    def _format_success_response(self, prompt: str, images: list) -> Dict[str, Any]:
        """格式化成功响应"""
        result = f"✅ 图片生成成功！\n\n"
        result += f"📝 描述：{prompt}\n\n"
        result += f"🖼️ 生成了 {len(images)} 张图片：\n"
        
        file_paths = []
        for i, img in enumerate(images, 1):
            local_path = img.get("local_path", "")
            if local_path:
                result += f"\n{i}. 本地路径：{local_path}"
                file_paths.append(local_path)
        
        result += "\n\n💡 您可以打开图片查看效果"
        
        return {
            "message": result,
            "file_paths": file_paths,
            "first_file_path": file_paths[0] if file_paths else None,
            "count": len(images),
            "prompt": prompt
        }

    def _get_help_info(self) -> str:
        """获取帮助信息"""
        return """🖼️ 图片生成智能体

功能：
- 文生图：根据文字描述生成图片
- 支持多种风格和尺寸

使用方法：
- "生成一张图片：夕阳下的海滩"
- "画一幅画：可爱的猫咪"
- "AI绘画：未来城市"

参数说明：
- prompt: 图片描述（必填）
- size: 图片尺寸，默认 1024*1024
- style: 风格，可选 <auto>, <photography>, <portrait> 等

注意：
- 需要配置 DASHSCOPE_API_KEY
- 图片会保存到 Pictures/AI_Generated 目录"""

    def get_capabilities_description(self) -> str:
        """获取能力描述，用于LLM意图识别"""
        return """### image_agent (图片生成智能体)
- 文生图: 根据文字描述生成图片，action=generate, prompt=图片描述
- 支持参数: size=尺寸(如1024*1024), style=风格
- 示例: "生成一张夕阳海滩的图片" -> action=generate, prompt="夕阳海滩"
"""
