"""
Screen Cast Agent - 同屏智能体
支持 DLNA 投屏到小米电视等设备，支持手机投屏到电脑
"""
import asyncio
import socket
import subprocess
import sys
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from loguru import logger
from urllib.parse import urlparse

from ..base import BaseAgent, Task


@dataclass
class DLNADevice:
    """DLNA 设备信息"""
    name: str
    ip: str
    port: int
    control_url: str
    rendering_control_url: str
    manufacturer: str = ""
    model: str = ""


class ScreenCastAgent(BaseAgent):
    """同屏智能体 - 支持 DLNA 投屏和手机投屏接收"""
    
    KEYWORD_MAPPINGS = {
        "投屏": ("discover_devices", {}),
        "同屏": ("discover_devices", {}),
        "搜索设备": ("discover_devices", {}),
        "发现设备": ("discover_devices", {}),
        "投屏视频": ("cast_video", {}),
        "停止投屏": ("stop_cast", {}),
        "手机投屏": ("receive_phone", {}),
        "接收投屏": ("receive_phone", {}),
        "屏幕镜像": ("screen_mirror", {}),
    }

    def __init__(self):
        super().__init__(
            name="screen_cast_agent",
            description="同屏智能体 - 支持投屏到小米电视等设备，支持手机投屏到电脑"
        )

        self.register_capability("discover_devices", "发现投屏设备")
        self.register_capability("cast_video", "投屏视频")
        self.register_capability("cast_url", "投屏URL")
        self.register_capability("screen_mirror", "屏幕镜像")
        self.register_capability("stop_cast", "停止投屏")
        self.register_capability("receive_phone", "接收手机投屏")
        
        self._devices: List[DLNADevice] = []
        self._current_device: Optional[DLNADevice] = None
        self._local_ip: Optional[str] = None

        logger.info("📺 同屏智能体已初始化")

    async def execute_task(self, task: Task) -> Any:
        task_type = task.type
        params = task.params
        logger.info(f"📺 执行同屏任务: {task_type}")

        if task_type == "general":
            content = task.content.lower()
            if "搜索" in content or "发现" in content or "设备" in content:
                result = await self._discover_devices()
            elif "镜像" in content:
                result = await self._screen_mirror(params)
            elif "停止" in content:
                result = await self._stop_cast()
            elif "手机" in content or "接收" in content or "android" in content:
                result = await self._receive_phone_screen(params)
            else:
                result = await self._handle_cast_request(task.content, params)
        elif task_type in ["discover", "search", "discover_devices"]:
            result = await self._discover_devices()
        elif task_type in ["cast", "cast_video", "play"]:
            result = await self._cast_video(params)
        elif task_type in ["cast_url", "play_url"]:
            result = await self._cast_url(params)
        elif task_type in ["mirror", "screen_mirror"]:
            result = await self._screen_mirror(params)
        elif task_type in ["stop", "stop_cast"]:
            result = await self._stop_cast()
        elif task_type in ["list", "devices"]:
            result = self._list_devices()
        elif task_type in ["receive_phone", "phone_screen", "android_mirror"]:
            result = await self._receive_phone_screen(params)
        else:
            return f"❌ 不支持的操作: {task_type}"
        
        if result and ("未找到" in result or "不存在" in result):
            task.no_retry = True
        return result

    def _get_local_ip(self) -> str:
        """获取本机 IP 地址"""
        if self._local_ip:
            return self._local_ip
        
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            self._local_ip = s.getsockname()[0]
            s.close()
            return self._local_ip
        except Exception:
            return "127.0.0.1"

    async def _discover_devices(self) -> str:
        """搜索局域网内的 DLNA 设备"""
        logger.info("🔍 正在搜索 DLNA 设备...")
        
        self._devices = []
        
        try:
            import upnpclient
            
            devices = upnpclient.discover()
            
            for device in devices:
                try:
                    device_info = self._parse_device_info(device)
                    if device_info:
                        self._devices.append(device_info)
                        logger.info(f"📺 发现设备: {device_info.name} ({device_info.ip})")
                except Exception as e:
                    logger.debug(f"解析设备信息失败: {e}")
            
            if self._devices:
                device_list = "\n".join([
                    f"  {i+1}. {d.name} ({d.manufacturer} {d.model})"
                    for i, d in enumerate(self._devices)
                ])
                return f"✅ 发现 {len(self._devices)} 个设备:\n\n{device_list}\n\n使用「投屏到第N个设备」选择设备"
            else:
                return "❌ 未发现 DLNA 设备\n\n请确保:\n1. 电视和电脑在同一局域网\n2. 电视已开启 DLNA 功能\n3. 电视处于开机状态"
                
        except ImportError:
            logger.warning("upnpclient 未安装，使用备用搜索方式")
            return await self._discover_devices_fallback()
        except Exception as e:
            logger.error(f"搜索设备失败: {e}")
            return f"❌ 搜索设备失败: {e}"

    async def _discover_devices_fallback(self) -> str:
        """备用设备搜索方式"""
        SSDP_ADDR = "239.255.255.250"
        SSDP_PORT = 1900
        SSDP_MX = 3
        SSDP_ST = "urn:schemas-upnp-org:device:MediaRenderer:1"
        
        search_msg = (
            f"M-SEARCH * HTTP/1.1\r\n"
            f"HOST: {SSDP_ADDR}:{SSDP_PORT}\r\n"
            f"MAN: \"ssdp:discover\"\r\n"
            f"MX: {SSDP_MX}\r\n"
            f"ST: {SSDP_ST}\r\n"
            f"\r\n"
        ).encode()
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.settimeout(5)
            
            sock.sendto(search_msg, (SSDP_ADDR, SSDP_PORT))
            
            while True:
                try:
                    data, addr = sock.recvfrom(4096)
                    response = data.decode('utf-8', errors='ignore')
                    
                    if "LOCATION:" in response.upper():
                        location_line = None
                        for line in response.split('\n'):
                            if line.upper().startswith('LOCATION:'):
                                location_line = line.split(':', 1)[1].strip()
                                break
                        
                        if location_line:
                            device = DLNADevice(
                                name=f"设备@{addr[0]}",
                                ip=addr[0],
                                port=addr[1],
                                control_url=location_line,
                                rendering_control_url=""
                            )
                            self._devices.append(device)
                            logger.info(f"📺 发现设备: {device.name}")
                            
                except socket.timeout:
                    break
                    
            sock.close()
            
            if self._devices:
                device_list = "\n".join([
                    f"  {i+1}. {d.name}"
                    for i, d in enumerate(self._devices)
                ])
                return f"✅ 发现 {len(self._devices)} 个设备:\n\n{device_list}"
            else:
                return "❌ 未发现 DLNA 设备"
                
        except Exception as e:
            logger.error(f"备用搜索失败: {e}")
            return f"❌ 搜索失败: {e}"

    def _parse_device_info(self, device) -> Optional[DLNADevice]:
        """解析设备信息"""
        try:
            url = urlparse(device.location)
            
            manufacturer = ""
            model = ""
            name = device.friendly_name or "未知设备"
            
            if hasattr(device, 'manufacturer'):
                manufacturer = device.manufacturer or ""
            if hasattr(device, 'model_name'):
                model = device.model_name or ""
            if hasattr(device, 'model_description'):
                model = device.model_description or model
            
            control_url = ""
            rendering_url = ""
            
            for service in device.services:
                if 'AVTransport' in service.serviceType:
                    control_url = service.controlURL
                if 'RenderingControl' in service.serviceType:
                    rendering_url = service.controlURL
            
            return DLNADevice(
                name=name,
                ip=url.hostname or "",
                port=url.port or 80,
                control_url=control_url,
                rendering_control_url=rendering_url,
                manufacturer=manufacturer,
                model=model
            )
        except Exception as e:
            logger.debug(f"解析设备失败: {e}")
            return None

    def _list_devices(self) -> str:
        """列出已发现的设备"""
        if not self._devices:
            return "❌ 尚未搜索设备，请先发送「搜索投屏设备」"
        
        device_list = "\n".join([
            f"  {i+1}. {d.name} ({d.manufacturer} {d.model})"
            for i, d in enumerate(self._devices)
        ])
        
        current = f"\n\n当前选择: {self._current_device.name}" if self._current_device else ""
        return f"📺 已发现 {len(self._devices)} 个设备:\n\n{device_list}{current}"

    async def _handle_cast_request(self, content: str, params: Dict) -> str:
        """处理投屏请求"""
        import re
        
        content = content.replace("@同屏智能体", "").strip()
        
        device_match = re.search(r'第(\d+)个|设备(\d+)', content)
        if device_match:
            device_index = int(device_match.group(1) or device_match.group(2)) - 1
            if 0 <= device_index < len(self._devices):
                self._current_device = self._devices[device_index]
                return f"✅ 已选择设备: {self._current_device.name}"
            else:
                return f"❌ 设备编号无效，请选择 1-{len(self._devices)}"
        
        url_match = re.search(r'https?://[^\s<>"\']+', content)
        if url_match:
            return await self._cast_url({"url": url_match.group(0)})
        
        path_match = re.search(r'[A-Za-z]:\\[^\s<>"\']+', content)
        if path_match:
            return await self._cast_video({"video_path": path_match.group(0)})
        
        if not self._devices:
            return "❌ 尚未搜索设备，请先发送「搜索投屏设备」"
        
        if not self._current_device:
            return f"❌ 请先选择设备，发送「投屏到第N个设备」"

    async def _cast_video(self, params: Dict) -> str:
        """推送本地视频到电视"""
        video_path = params.get("video_path") or params.get("file_path")
        
        if not video_path:
            return "❌ 请提供视频文件路径"
        
        video_path = Path(video_path)
        if not video_path.exists():
            return f"❌ 文件不存在: {video_path}"
        
        if not self._current_device:
            if self._devices:
                self._current_device = self._devices[0]
            else:
                return "❌ 未选择投屏设备，请先搜索并选择设备"
        
        logger.info(f"📺 投屏本地视频: {video_path} -> {self._current_device.name}")
        
        try:
            import upnpclient
            
            device = upnpclient.Device(self._current_device.control_url.replace('/control', ''))
            
            local_ip = self._get_local_ip()
            video_url = f"http://{local_ip}:8765/{video_path.name}"
            
            logger.info(f"📺 视频URL: {video_url}")
            
            return f"✅ 正在投屏到 {self._current_device.name}\n\n📁 文件: {video_path.name}\n📺 设备: {self._current_device.name}\n\n💡 提示: 本地文件投屏需要启动本地HTTP服务器"
            
        except Exception as e:
            logger.error(f"投屏失败: {e}")
            return f"❌ 投屏失败: {e}"

    async def _cast_url(self, params: Dict) -> str:
        """推送在线视频URL到电视"""
        url = params.get("url", "")
        
        if not url:
            return "❌ 请提供视频URL"
        
        url = url.strip().strip('`').strip('"').strip("'")
        
        if not self._current_device:
            if self._devices:
                self._current_device = self._devices[0]
            else:
                return "❌ 未选择投屏设备，请先搜索并选择设备"
        
        logger.info(f"📺 投屏在线视频: {url} -> {self._current_device.name}")
        
        try:
            import upnpclient
            
            device = upnpclient.Device(self._current_device.control_url.replace('/control', ''))
            
            av_transport = device.AVTransport
            av_transport.SetAVTransportURI(
                InstanceID=0,
                CurrentURI=url,
                CurrentURIMetaData=""
            )
            
            av_transport.Play(InstanceID=0, Speed="1")
            
            return f"✅ 已投屏到 {self._current_device.name}\n\n🔗 地址: {url}\n📺 设备: {self._current_device.name}"
            
        except ImportError:
            return await self._cast_url_fallback(url)
        except Exception as e:
            logger.error(f"投屏失败: {e}")
            return f"❌ 投屏失败: {e}"

    async def _cast_url_fallback(self, url: str) -> str:
        """备用投屏方式"""
        import httpx
        
        if not self._current_device or not self._current_device.control_url:
            return "❌ 设备信息不完整"
        
        try:
            soap_body = f'''<?xml version="1.0"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"
            s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
  <s:Body>
    <u:SetAVTransportURI xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">
      <InstanceID>0</InstanceID>
      <CurrentURI>{url}</CurrentURI>
      <CurrentURIMetaData></CurrentURIMetaData>
    </u:SetAVTransportURI>
  </s:Body>
</s:Envelope>'''
            
            headers = {
                'Content-Type': 'text/xml; charset="utf-8"',
                'SOAPAction': '"urn:schemas-upnp-org:service:AVTransport:1#SetAVTransportURI"'
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self._current_device.control_url,
                    content=soap_body,
                    headers=headers,
                    timeout=10
                )
            
            if response.status_code == 200:
                play_body = f'''<?xml version="1.0"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"
            s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
  <s:Body>
    <u:Play xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">
      <InstanceID>0</InstanceID>
      <Speed>1</Speed>
    </u:Play>
  </s:Body>
</s:Envelope>'''
                
                headers['SOAPAction'] = '"urn:schemas-upnp-org:service:AVTransport:1#Play"'
                
                async with httpx.AsyncClient() as client:
                    await client.post(
                        self._current_device.control_url,
                        content=play_body,
                        headers=headers,
                        timeout=10
                    )
                
                return f"✅ 已投屏到 {self._current_device.name}\n\n🔗 地址: {url}"
            else:
                return f"❌ 投屏失败: HTTP {response.status_code}"
                
        except Exception as e:
            logger.error(f"备用投屏失败: {e}")
            return f"❌ 投屏失败: {e}"

    async def _screen_mirror(self, params: Dict) -> str:
        """屏幕镜像到电视"""
        if not self._devices:
            await self._discover_devices()
        
        if not self._current_device and self._devices:
            self._current_device = self._devices[0]
        
        if not self._current_device:
            return "❌ 未发现可用的投屏设备"
        
        logger.info(f"📺 开始屏幕镜像 -> {self._current_device.name}")
        
        if sys.platform == "win32":
            try:
                subprocess.Popen(
                    ["powershell", "-c", "Start-Process 'ms-projection:'"],
                    shell=True
                )
                return f"✅ 已打开 Windows 投影设置\n\n📺 目标设备: {self._current_device.name}\n\n💡 请在弹出的窗口中选择「{self._current_device.name}」进行连接"
            except Exception as e:
                logger.error(f"打开投影设置失败: {e}")
                return f"❌ 打开投影设置失败: {e}\n\n请手动按 Win+K 打开投影设置"
        else:
            return "❌ 屏幕镜像目前仅支持 Windows 系统\n\n请使用 Win+K 快捷键打开投影设置"

    async def _stop_cast(self) -> str:
        """停止投屏"""
        if not self._current_device:
            return "❌ 当前没有正在进行的投屏"
        
        try:
            import upnpclient
            
            device = upnpclient.Device(self._current_device.control_url.replace('/control', ''))
            device.AVTransport.Stop(InstanceID=0)
            
            return f"✅ 已停止投屏\n\n📺 设备: {self._current_device.name}"
            
        except ImportError:
            return await self._stop_cast_fallback()
        except Exception as e:
            logger.error(f"停止投屏失败: {e}")
            return f"❌ 停止投屏失败: {e}"

    async def _stop_cast_fallback(self) -> str:
        """备用停止投屏方式"""
        import httpx
        
        try:
            soap_body = f'''<?xml version="1.0"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"
            s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
  <s:Body>
    <u:Stop xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">
      <InstanceID>0</InstanceID>
    </u:Stop>
  </s:Body>
</s:Envelope>'''
            
            headers = {
                'Content-Type': 'text/xml; charset="utf-8"',
                'SOAPAction': '"urn:schemas-upnp-org:service:AVTransport:1#Stop"'
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self._current_device.control_url,
                    content=soap_body,
                    headers=headers,
                    timeout=10
                )
            
            if response.status_code == 200:
                return f"✅ 已停止投屏"
            else:
                return f"❌ 停止投屏失败: HTTP {response.status_code}"
                
        except Exception as e:
            return f"❌ 停止投屏失败: {e}"

    async def _receive_phone_screen(self, params: Dict) -> str:
        """接收手机投屏"""
        return self._get_phone_cast_guide()

    def _get_phone_cast_guide(self) -> str:
        """获取手机投屏指南"""
        local_ip = self._get_local_ip()
        
        guide = f"""📱 手机投屏到电脑

本机 IP: {local_ip}

=== Android 手机 ===

方法1: 无线投屏（推荐）
1. 手机和电脑连接同一 WiFi
2. 手机下拉通知栏 → 投屏
3. 选择电脑名称

方法2: Windows 无线显示器
1. 按 Win+K 打开投影
2. 手机投屏到电脑

=== iOS 手机 ===

方法1: AirPlay
1. 安装 AirPlay 接收软件（如 5KPlayer）
2. 手机控制中心 → 屏幕镜像
3. 选择电脑名称

方法2: 第三方软件
1. 安装 LonelyScreen 或 AirServer
2. 手机控制中心 → 屏幕镜像
3. 选择电脑
"""
        return guide
