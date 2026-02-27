from loguru import logger
from typing import Dict, Any, Optional, List
from ..base import BaseAgent, Task
from PIL import Image
import os
import pathlib
import glob


class ImageConverterAgent(BaseAgent):
    PRIORITY: int = 5
    
    KEYWORD_MAPPINGS: Dict[str, tuple] = {
        "图片转换": ("convert", {}),
        "格式转换": ("convert", {}),
        "png转jpg": ("convert", {"target_format": "jpg"}),
        "jpg转png": ("convert", {"target_format": "png"}),
        "转换图片": ("convert", {}),
        "图片格式": ("convert", {}),
        "批量转换": ("batch_convert", {}),
        "调整图片尺寸": ("resize", {}),
        "把图片缩小": ("resize", {}),
        "把图片缩小到": ("resize", {}),
    }
    
    SUPPORTED_FORMATS = {"png", "jpg", "jpeg", "webp", "bmp", "gif", "tiff"}
    
    def __init__(self):
        super().__init__(name="image_converter_agent", description="图片格式转换智能体 - 支持多种图片格式之间的转换（PNG、JPG、WEBP、BMP、GIF等）")
    
    def _get_pictures_dir(self) -> pathlib.Path:
        """获取图片保存目录"""
        try:
            from ...config import settings
            pictures_dir = settings.directory.get_pictures_dir()
            return pictures_dir / "Converted"
        except Exception as e:
            logger.warning(f"获取图片目录失败: {e}")
            return pathlib.Path.home() / "Pictures" / "Converted"
    
    async def execute_task(self, task: Task) -> Any:
        task_type = task.type
        params = task.params or {}
        
        if task_type == "convert":
            return await self._convert_image(params)
        elif task_type == "resize":
            return await self._resize_image(params)
        elif task_type == "batch_convert":
            return await self._batch_convert(params)
        elif task_type == "action":
            action = params.get("action")
            if action == "convert":
                return await self._convert_image(params)
            elif action == "resize":
                return await self._resize_image(params)
            elif action == "batch_convert":
                return await self._batch_convert(params)
        
        elif task_type == "agent_help":
            return self._get_help_info()
        
        return self.cannot_handle(f"未知操作: {task_type}")
    
    async def _convert_image(self, params: Dict) -> str:
        source_path = params.get("source_path")
        target_format = params.get("target_format", "").lower()
        quality = params.get("quality", 85)
        
        if not source_path or not os.path.exists(source_path):
            return self.cannot_handle("源文件不存在")
        if not target_format or target_format not in self.SUPPORTED_FORMATS:
            return self.cannot_handle(f"不支持的目标格式。支持的格式: {', '.join(self.SUPPORTED_FORMATS)}")
        
        try:
            img = Image.open(source_path)
            if target_format in ["jpg", "jpeg"] and img.mode in ("RGBA", "LA", "P"):
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
                img = background
            elif target_format == "png" and img.mode == "RGB":
                img = img.convert("RGBA")
            
            output_dir = self._get_pictures_dir()
            output_dir.mkdir(parents=True, exist_ok=True)
            
            source_name = pathlib.Path(source_path).stem
            output_path = output_dir / f"{source_name}.{target_format}"
            if output_path.exists():
                output_path = output_dir / f"{source_name}_converted.{target_format}"
            
            save_kwargs = {}
            if target_format in ["jpg", "jpeg", "webp"]:
                save_kwargs["quality"] = quality
            img.save(output_path, format=target_format.upper(), **save_kwargs)
            return f"✅ 已转换: {output_path}"
        except Exception as e:
            return self.cannot_handle(f"转换失败: {e}")
    
    async def _resize_image(self, params: Dict) -> str:
        source_path = params.get("source_path") or params.get("image_path")
        width = params.get("width")
        height = params.get("height")
        scale = params.get("scale")
        size = params.get("size")
        
        if not source_path or not os.path.exists(source_path):
            return self.cannot_handle("源文件不存在")
        
        try:
            img = Image.open(source_path)
            orig_w, orig_h = img.size
            
            if scale is not None:
                new_w = int(orig_w * scale)
                new_h = int(orig_h * scale)
            elif size:
                if isinstance(size, str) and "x" in size.lower():
                    parts = size.lower().split("x")
                    if len(parts) == 2:
                        try:
                            new_w = int(parts[0].strip())
                            new_h = int(parts[1].strip())
                        except ValueError:
                            return self.cannot_handle("无效的尺寸格式，请使用如 '128x128' 的格式")
                else:
                    return self.cannot_handle("无效的尺寸格式，请使用如 '128x128' 的格式")
            else:
                new_w = width if width is not None else orig_w
                new_h = height if height is not None else orig_h
            
            if new_w <= 0 or new_h <= 0:
                return self.cannot_handle("无效的尺寸参数")
            
            resized_img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            
            output_dir = self._get_pictures_dir()
            output_dir.mkdir(parents=True, exist_ok=True)
            
            source_name = pathlib.Path(source_path).stem
            source_ext = pathlib.Path(source_path).suffix
            output_path = output_dir / f"{source_name}_resized{source_ext}"
            
            resized_img.save(output_path)
            return f"✅ 已调整尺寸: {output_path} ({new_w}x{new_h})"
        except Exception as e:
            return self.cannot_handle(f"调整尺寸失败: {e}")
    
    async def _batch_convert(self, params: Dict) -> str:
        source_dir = params.get("source_dir")
        target_format = params.get("target_format", "").lower()
        
        if not source_dir or not os.path.isdir(source_dir):
            return self.cannot_handle("源文件夹不存在")
        if not target_format or target_format not in self.SUPPORTED_FORMATS:
            return self.cannot_handle(f"不支持的目标格式。支持的格式: {', '.join(self.SUPPORTED_FORMATS)}")
        
        try:
            files = []
            for ext in ["*.png", "*.jpg", "*.jpeg", "*.webp", "*.bmp", "*.gif", "*.tiff"]:
                files.extend(glob.glob(os.path.join(source_dir, ext)))
                files.extend(glob.glob(os.path.join(source_dir, ext.upper())))
            
            if not files:
                return self.cannot_handle("源文件夹中没有找到支持的图片文件")
            
            converted = 0
            for file_path in files:
                try:
                    result = await self._convert_image({"source_path": file_path, "target_format": target_format})
                    if result.startswith("✅"):
                        converted += 1
                except:
                    continue
            
            return f"✅ 批量转换完成: {converted}/{len(files)} 个文件"
        except Exception as e:
            return self.cannot_handle(f"批量转换失败: {e}")