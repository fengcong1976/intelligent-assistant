"""
QR Code Generator Skill Executor
OpenClaw compatible skill implementation
"""
import asyncio
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

try:
    import qrcode
    from PIL import Image
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "qrcode", "pillow"])
    import qrcode
    from PIL import Image


def get_desktop_path() -> Path:
    """Get desktop path for current user"""
    if sys.platform == "win32":
        desktop = Path.home() / "Desktop"
        if not desktop.exists():
            desktop = Path.home() / "桌面"
    else:
        desktop = Path.home() / "Desktop"
    
    if not desktop.exists():
        desktop = Path.home()
    
    return desktop


async def generate_qr(
    text: str,
    size: int = 300,
    color: str = "black",
    save_path: Optional[str] = None
) -> dict:
    """
    Generate QR code
    
    Args:
        text: Content to encode
        size: QR code size in pixels (default 300)
        color: Fill color (default black)
        save_path: Save path (default desktop)
    
    Returns:
        dict with success status and file path
    """
    if not text:
        return {
            "success": False,
            "error": "请提供需要生成二维码的内容"
        }
    
    size = max(100, min(1000, size))
    
    if save_path is None:
        desktop = get_desktop_path()
        save_path = str(desktop / "qr_code.png")
    
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(text)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color=color, back_color="white")
        
        if size != 300:
            img = img.resize((size, size), Image.Resampling.LANCZOS)
        
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        img.save(save_path)
        
        return {
            "success": True,
            "file_path": save_path,
            "message": f"二维码生成成功！已保存到：{save_path}"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"生成二维码失败：{str(e)}"
        }


async def execute(**kwargs):
    """Main entry point for skill execution"""
    return await generate_qr(**kwargs)


if __name__ == "__main__":
    import asyncio
    result = asyncio.run(generate_qr("https://github.com/openclaw/openclaw"))
    print(result)
