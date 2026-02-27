"""
操作系统智能体 - 全面控制 Windows 系统
功能包括：音量、电源、WiFi、进程、窗口、剪贴板、系统信息、应用程序、网络、服务等
"""
import asyncio
import subprocess
import platform
import os
import json
import ctypes
from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger

from ..base import BaseAgent, Task


class OSAgent(BaseAgent):
    """操作系统智能体 - 全面控制系统功能"""
    
    PRIORITY = 1
    KEYWORD_MAPPINGS = {
        # 音量控制
        "关机": ("shutdown", {}),
        "重启": ("restart", {}),
        "注销": ("logout", {}),
        "锁屏": ("lock", {}),
        "休眠": ("sleep", {}),
        "睡眠": ("sleep", {}),
        "截图": ("screenshot", {}),
        "截屏": ("screenshot", {}),
        "录屏": ("screen_record", {}),
        "屏幕录制": ("screen_record", {}),
        "音量": ("volume_get", {}),
        "当前音量": ("volume_get", {}),
        "静音": ("volume_mute", {}),
        "取消静音": ("volume_unmute", {}),
        "声音大一点": ("volume_up", {}),
        "声音小一点": ("volume_down", {}),
        "大声点": ("volume_up", {}),
        "小声点": ("volume_down", {}),
        "音量大一点": ("volume_up", {}),
        "音量小一点": ("volume_down", {}),
        "音量调高点": ("volume_up", {}),
        "音量调低点": ("volume_down", {}),
        "调大音量": ("volume_up", {}),
        "调小音量": ("volume_down", {}),
        "增加音量": ("volume_up", {}),
        "降低音量": ("volume_down", {}),
        "音量加": ("volume_up", {}),
        "音量减": ("volume_down", {}),
        "把声音调大": ("volume_up", {}),
        "把声音调小": ("volume_down", {}),
        "把音量调大": ("volume_up", {}),
        "把音量调小": ("volume_down", {}),
        "声音调大": ("volume_up", {}),
        "声音调小": ("volume_down", {}),
        "音量调大": ("volume_up", {}),
        "音量调小": ("volume_down", {}),
        "调大声": ("volume_up", {}),
        "调小声": ("volume_down", {}),
        "声音大": ("volume_up", {}),
        "声音小": ("volume_down", {}),
        # WiFi和网络
        "WiFi": ("wifi_status", {}),
        "WiFi状态": ("wifi_status", {}),
        "网络": ("network_info", {}),
        "网络状态": ("network_info", {}),
        "蓝牙": ("bluetooth_status", {}),
        "蓝牙状态": ("bluetooth_status", {}),
        # 音频设备
        "音频设备": ("audio_list", {}),
        "声音设备": ("audio_list", {}),
        "音频设备列表": ("audio_list", {}),
        "声音设备列表": ("audio_list", {}),
        "列出音频设备": ("audio_list", {}),
        "列出声音设备": ("audio_list", {}),
        "切换音频输出": ("audio_output_switch", {}),
        "切换声音输出": ("audio_output_switch", {}),
        "切换扬声器": ("audio_output_switch", {}),
        "切换输出设备": ("audio_output_switch", {}),
        "切换音频输入": ("audio_input_switch", {}),
        "切换声音输入": ("audio_input_switch", {}),
        "切换麦克风": ("audio_input_switch", {}),
        "切换输入设备": ("audio_input_switch", {}),
        "默认扬声器": ("audio_output_default", {}),
        "默认麦克风": ("audio_input_default", {}),
        # 电池和电源
        "电池": ("battery_status", {}),
        "电量": ("battery_status", {}),
        "电池状态": ("battery_status", {}),
        # 系统信息
        "系统信息": ("system_info", {}),
        "电脑信息": ("system_info", {}),
        "CPU": ("cpu_info", {}),
        "CPU使用率": ("cpu_info", {}),
        "内存": ("memory_info", {}),
        "内存使用": ("memory_info", {}),
        "磁盘": ("disk_info", {}),
        "磁盘空间": ("disk_info", {}),
        "硬盘空间": ("disk_info", {}),
        # 进程管理
        "进程列表": ("process_list", {}),
        "运行中的程序": ("process_list", {}),
        "进程": ("process_list", {}),
        # 剪贴板
        "剪贴板": ("clipboard_get", {}),
        "粘贴板": ("clipboard_get", {}),
        "复制的内容": ("clipboard_get", {}),
        # 应用程序
        "打开": ("app_open", {}),
        "运行": ("app_open", {}),
        "启动": ("app_open", {}),
        "关闭程序": ("app_close", {}),
        "结束程序": ("app_kill", {}),
        "强制关闭": ("app_kill", {}),
        # 窗口管理
        "最小化": ("window_minimize", {}),
        "最大化": ("window_maximize", {}),
        "关闭窗口": ("window_close", {}),
        # 服务管理
        "服务列表": ("service_list", {}),
        "启动服务": ("service_start", {}),
        "停止服务": ("service_stop", {}),
        # 系统设置
        "壁纸": ("wallpaper_get", {}),
        "桌面壁纸": ("wallpaper_get", {}),
        "换壁纸": ("wallpaper_set", {}),
        "更换壁纸": ("wallpaper_set", {}),
        # 时间和日期
        "现在几点": ("time_now", {}),
        "当前时间": ("time_now", {}),
        "现在时间": ("time_now", {}),
        "今天日期": ("date_today", {}),
        "今天是几号": ("date_today", {}),
        # 清理和维护
        "清理垃圾": ("clean_temp", {}),
        "清理临时文件": ("clean_temp", {}),
        "清空回收站": ("empty_recycle", {}),
        "回收站": ("empty_recycle", {}),
        # 显示器
        "亮度": ("brightness_get", {}),
        "屏幕亮度": ("brightness_get", {}),
        "调亮": ("brightness_up", {}),
        "调暗": ("brightness_down", {}),
        "关闭显示器": ("monitor_off", {}),
        "息屏": ("monitor_off", {}),
        # 通知
        "通知": ("notification", {}),
        "提醒我": ("notification", {}),
    }

    def __init__(self):
        super().__init__(
            name="os_agent",
            description="操作系统智能体 - 全面控制 Windows 系统"
        )
        
        self.register_capability(
            capability="system_control",
            description="执行系统控制操作。支持音量控制、截屏、锁屏、关机等操作。",
            aliases=[
                "系统关机", "电脑关机", "关电脑", "关机", "关闭电脑", "关闭系统",
                "系统重启", "电脑重启", "重启电脑", "重启", "重启系统",
                "系统注销", "注销系统", "注销", "退出登录",
                "锁屏", "锁住屏幕", "锁定屏幕", "锁电脑",
                "系统休眠", "电脑休眠", "休眠", "睡眠", "系统睡眠", "电脑睡眠",
                "系统截图", "电脑截图", "截图", "截屏", "抓屏", "屏幕截图",
                "系统录屏", "电脑录屏", "录屏", "屏幕录制", "录制屏幕",
                "系统音量", "电脑音量", "音量", "当前音量", "查看音量",
                "系统静音", "电脑静音", "静音", "静音系统", "静音电脑",
                "取消静音", "取消系统静音", "取消电脑静音",
                "系统音量大一点", "电脑音量大一点", "声音大一点", "大声点", "调大音量",
                "系统音量小一点", "电脑音量小一点", "声音小一点", "小声点", "调小音量",
                "系统WiFi", "电脑WiFi", "WiFi", "WiFi状态", "查看WiFi",
                "系统网络", "电脑网络", "网络", "网络状态", "查看网络",
                "系统蓝牙", "电脑蓝牙", "蓝牙", "蓝牙状态", "查看蓝牙",
                "系统电池", "电脑电池", "电池", "电量", "电池状态", "查看电池",
                "系统信息", "电脑信息", "系统详情", "电脑详情", "查看系统信息",
                "系统配置", "电脑配置", "系统版本", "电脑版本", "系统设置", "电脑设置",
                "打开设置", "打开系统设置", "打开电脑设置",
                "系统CPU", "电脑CPU", "CPU", "CPU使用率", "查看CPU",
                "系统内存", "电脑内存", "内存", "内存使用", "查看内存",
                "系统磁盘", "电脑磁盘", "磁盘", "磁盘空间", "硬盘空间", "查看磁盘",
                "系统进程", "电脑进程", "进程列表", "运行中的程序", "查看进程",
                "系统剪贴板", "电脑剪贴板", "剪贴板", "粘贴板", "查看剪贴板",
                "清理系统垃圾", "清理电脑垃圾", "清理垃圾", "清理临时文件",
                "清空回收站", "清理回收站", "回收站",
                "系统亮度", "电脑亮度", "屏幕亮度", "亮度", "查看亮度",
                "关闭显示器", "息屏", "关闭屏幕",
                "系统通知", "电脑通知", "通知", "提醒我"
            ],
            alias_params={
                "系统关机": {"command": "关机"},
                "电脑关机": {"command": "关机"},
                "关电脑": {"command": "关机"},
                "关机": {"command": "关机"},
                "关闭电脑": {"command": "关机"},
                "关闭系统": {"command": "关机"},
                "系统重启": {"command": "重启"},
                "电脑重启": {"command": "重启"},
                "重启电脑": {"command": "重启"},
                "重启": {"command": "重启"},
                "重启系统": {"command": "重启"},
                "系统注销": {"command": "注销"},
                "注销系统": {"command": "注销"},
                "注销": {"command": "注销"},
                "退出登录": {"command": "注销"},
                "锁屏": {"command": "锁屏"},
                "锁住屏幕": {"command": "锁屏"},
                "锁定屏幕": {"command": "锁屏"},
                "锁电脑": {"command": "锁屏"},
                "系统休眠": {"command": "休眠"},
                "电脑休眠": {"command": "休眠"},
                "休眠": {"command": "休眠"},
                "睡眠": {"command": "休眠"},
                "系统睡眠": {"command": "休眠"},
                "电脑睡眠": {"command": "休眠"},
                "系统截图": {"command": "截图"},
                "电脑截图": {"command": "截图"},
                "截图": {"command": "截图"},
                "截屏": {"command": "截图"},
                "抓屏": {"command": "截图"},
                "屏幕截图": {"command": "截图"},
                "系统录屏": {"command": "录屏"},
                "电脑录屏": {"command": "录屏"},
                "录屏": {"command": "录屏"},
                "屏幕录制": {"command": "录屏"},
                "录制屏幕": {"command": "录屏"},
                "系统音量": {"command": "查看音量"},
                "电脑音量": {"command": "查看音量"},
                "音量": {"command": "查看音量"},
                "当前音量": {"command": "查看音量"},
                "查看音量": {"command": "查看音量"},
                "系统静音": {"command": "静音"},
                "电脑静音": {"command": "静音"},
                "静音": {"command": "静音"},
                "静音系统": {"command": "静音"},
                "静音电脑": {"command": "静音"},
                "取消静音": {"command": "取消静音"},
                "取消系统静音": {"command": "取消静音"},
                "取消电脑静音": {"command": "取消静音"},
                "系统音量大一点": {"command": "音量调高"},
                "电脑音量大一点": {"command": "音量调高"},
                "声音大一点": {"command": "音量调高"},
                "大声点": {"command": "音量调高"},
                "调大音量": {"command": "音量调高"},
                "系统音量小一点": {"command": "音量调低"},
                "电脑音量小一点": {"command": "音量调低"},
                "声音小一点": {"command": "音量调低"},
                "小声点": {"command": "音量调低"},
                "调小音量": {"command": "音量调低"},
                "系统WiFi": {"command": "查看WiFi"},
                "电脑WiFi": {"command": "查看WiFi"},
                "WiFi": {"command": "查看WiFi"},
                "WiFi状态": {"command": "查看WiFi"},
                "查看WiFi": {"command": "查看WiFi"},
                "系统网络": {"command": "查看网络"},
                "电脑网络": {"command": "查看网络"},
                "网络": {"command": "查看网络"},
                "网络状态": {"command": "查看网络"},
                "查看网络": {"command": "查看网络"},
                "系统蓝牙": {"command": "查看蓝牙"},
                "电脑蓝牙": {"command": "查看蓝牙"},
                "蓝牙": {"command": "查看蓝牙"},
                "蓝牙状态": {"command": "查看蓝牙"},
                "查看蓝牙": {"command": "查看蓝牙"},
                "系统电池": {"command": "查看电池"},
                "电脑电池": {"command": "查看电池"},
                "电池": {"command": "查看电池"},
                "电量": {"command": "查看电池"},
                "电池状态": {"command": "查看电池"},
                "查看电池": {"command": "查看电池"},
                "系统信息": {"command": "查看系统信息"},
                "电脑信息": {"command": "查看系统信息"},
                "系统详情": {"command": "查看系统信息"},
                "电脑详情": {"command": "查看系统信息"},
                "查看系统信息": {"command": "查看系统信息"},
                "系统配置": {"command": "查看系统信息"},
                "电脑配置": {"command": "查看系统信息"},
                "系统版本": {"command": "查看系统信息"},
                "电脑版本": {"command": "查看系统信息"},
                "系统设置": {"command": "打开设置"},
                "电脑设置": {"command": "打开设置"},
                "打开设置": {"command": "打开设置"},
                "打开系统设置": {"command": "打开设置"},
                "打开电脑设置": {"command": "打开设置"},
                "系统CPU": {"command": "查看CPU"},
                "电脑CPU": {"command": "查看CPU"},
                "CPU": {"command": "查看CPU"},
                "CPU使用率": {"command": "查看CPU"},
                "查看CPU": {"command": "查看CPU"},
                "系统内存": {"command": "查看内存"},
                "电脑内存": {"command": "查看内存"},
                "内存": {"command": "查看内存"},
                "内存使用": {"command": "查看内存"},
                "查看内存": {"command": "查看内存"},
                "系统磁盘": {"command": "查看磁盘"},
                "电脑磁盘": {"command": "查看磁盘"},
                "磁盘": {"command": "查看磁盘"},
                "磁盘空间": {"command": "查看磁盘"},
                "硬盘空间": {"command": "查看磁盘"},
                "查看磁盘": {"command": "查看磁盘"},
                "系统进程": {"command": "查看进程"},
                "电脑进程": {"command": "查看进程"},
                "进程列表": {"command": "查看进程"},
                "运行中的程序": {"command": "查看进程"},
                "查看进程": {"command": "查看进程"},
                "系统剪贴板": {"command": "查看剪贴板"},
                "电脑剪贴板": {"command": "查看剪贴板"},
                "剪贴板": {"command": "查看剪贴板"},
                "粘贴板": {"command": "查看剪贴板"},
                "查看剪贴板": {"command": "查看剪贴板"},
                "清理系统垃圾": {"command": "清理垃圾"},
                "清理电脑垃圾": {"command": "清理垃圾"},
                "清理垃圾": {"command": "清理垃圾"},
                "清理临时文件": {"command": "清理垃圾"},
                "清空回收站": {"command": "清空回收站"},
                "清理回收站": {"command": "清空回收站"},
                "回收站": {"command": "清空回收站"},
                "系统亮度": {"command": "查看亮度"},
                "电脑亮度": {"command": "查看亮度"},
                "屏幕亮度": {"command": "查看亮度"},
                "亮度": {"command": "查看亮度"},
                "查看亮度": {"command": "查看亮度"},
                "关闭显示器": {"command": "息屏"},
                "息屏": {"command": "息屏"},
                "关闭屏幕": {"command": "息屏"},
                "系统通知": {"command": "查看通知"},
                "电脑通知": {"command": "查看通知"},
                "通知": {"command": "查看通知"},
                "提醒我": {"command": "设置提醒"}
            },
            parameters={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "系统操作命令，如'音量调高'、'音量调低'、'静音'、'截屏'、'锁屏'、'关机'、'重启'等"
                    }
                },
                "required": ["command"]
            },
            category="system"
        )
        
        self.register_capability(
            capability="clipboard_write",
            description="将文本复制到剪贴板。当用户说'复制xxx'、'把xxx复制到剪贴板'时调用此工具。",
            parameters={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "要复制到剪贴板的文本内容"
                    }
                },
                "required": ["text"]
            },
            category="system"
        )
        
        self.register_capability(
            capability="take_screenshot",
            description="截取屏幕截图并保存。当用户说'截图'、'截屏'、'抓屏'时调用此工具。截图会自动保存到桌面。",
            parameters={
                "type": "object",
                "properties": {
                    "region": {
                        "type": "string",
                        "description": "截图区域（可选）：'full'全屏、'window'当前窗口，默认全屏",
                        "default": "full"
                    }
                },
                "required": []
            },
            category="system"
        )
        
        self.register_capability(
            capability="audio_device_control",
            description="控制音频设备。支持列出音频设备、切换音频输出设备（扬声器）、切换音频输入设备（麦克风）。",
            aliases=[
                "音频设备", "声音设备", "音频设备列表", "声音设备列表",
                "列出音频设备", "列出声音设备",
                "切换音频输出", "切换声音输出", "切换扬声器", "切换输出设备",
                "切换音频输入", "切换声音输入", "切换麦克风", "切换输入设备",
                "默认扬声器", "默认麦克风"
            ],
            alias_params={
                "音频设备": {"operation": "list"},
                "声音设备": {"operation": "list"},
                "音频设备列表": {"operation": "list"},
                "声音设备列表": {"operation": "list"},
                "列出音频设备": {"operation": "list"},
                "列出声音设备": {"operation": "list"},
                "切换音频输出": {"operation": "switch_output"},
                "切换声音输出": {"operation": "switch_output"},
                "切换扬声器": {"operation": "switch_output"},
                "切换输出设备": {"operation": "switch_output"},
                "切换音频输入": {"operation": "switch_input"},
                "切换声音输入": {"operation": "switch_input"},
                "切换麦克风": {"operation": "switch_input"},
                "切换输入设备": {"operation": "switch_input"},
                "默认扬声器": {"operation": "default_output"},
                "默认麦克风": {"operation": "default_input"}
            },
            parameters={
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["list", "switch_output", "switch_input", "default_output", "default_input"],
                        "description": "操作类型：list(列出设备)、switch_output(切换输出设备)、switch_input(切换输入设备)、default_output(设置默认输出)、default_input(设置默认输入)"
                    },
                    "device": {
                        "type": "string",
                        "description": "设备名称或索引（切换设备时使用）"
                    }
                },
                "required": ["operation"]
            },
            category="system"
        )
        
        self.system = platform.system()
        logger.info(f"🖥️ 操作系统智能体已初始化 (系统: {self.system})")

    async def execute_task(self, task: Task) -> str:
        """执行任务"""
        params = task.params
        
        action = params.get("action", "") or params.get("command", "")
        if not action:
            if task.type == "audio_device_control":
                action = "audio_device_control"
            else:
                action = task.type.replace("system_control", "").replace("_control", "").strip()
        
        if task.type == "general":
            action = self._parse_general_action(params.get("text", ""))
        
        action = action.lower()
        
        if action in self.KEYWORD_MAPPINGS:
            action, extra_params = self.KEYWORD_MAPPINGS[action]
            params.update(extra_params)

        logger.info(f"🖥️ OS Agent 执行: {action}")

        try:
            # 帮助
            if action in ("help", "?", "？", "/?", "/？"):
                return self._get_help()
            
            # ==================== 音量控制 ====================
            elif action == "volume_set":
                return await self._set_volume(params.get("level", 50))
            elif action == "volume_get":
                return await self._get_volume()
            elif action == "volume_mute":
                return await self._mute_volume()
            elif action == "volume_unmute":
                return await self._unmute_volume()
            elif action == "volume_up":
                return await self._volume_up()
            elif action == "volume_down":
                return await self._volume_down()
            elif action == "volume_control":
                operation = params.get("operation", "")
                if operation in ("increase", "up"):
                    return await self._volume_up()
                elif operation in ("decrease", "down"):
                    return await self._volume_down()
                elif operation == "mute":
                    return await self._mute_volume()
                elif operation == "unmute":
                    return await self._unmute_volume()
                else:
                    return await self._get_volume()
            
            # ==================== 系统电源 ====================
            elif action == "lock":
                return await self._lock_screen()
            elif action == "logout":
                return await self._logout()
            elif action == "screenshot":
                return await self._screenshot()
            elif action == "take_screenshot":
                return await self._screenshot()
            elif action == "screen_record":
                return await self._screen_record()
            elif action == "sleep":
                return await self._sleep_system()
            elif action == "shutdown":
                return await self._shutdown_system()
            elif action == "restart":
                return await self._restart_system()
            
            # ==================== WiFi 和网络 ====================
            elif action == "wifi_list":
                return await self._list_wifi()
            elif action == "wifi_connect":
                return await self._connect_wifi(params.get("ssid"), params.get("password"))
            elif action == "wifi_disconnect":
                return await self._disconnect_wifi()
            elif action == "wifi_status":
                return await self._wifi_status()
            elif action == "network_info":
                return await self._network_info()
            elif action == "bluetooth_status":
                return await self._bluetooth_status()
            
            # ==================== 电池状态 ====================
            elif action == "battery_status":
                return await self._battery_status()
            
            # ==================== 系统信息 ====================
            elif action == "system_info":
                return await self._system_info()
            elif action == "cpu_info":
                return await self._cpu_info()
            elif action == "memory_info":
                return await self._memory_info()
            elif action == "disk_info":
                return await self._disk_info()
            
            # ==================== 进程管理 ====================
            elif action == "process_list":
                return await self._process_list(params.get("filter"))
            elif action == "process_kill":
                return await self._process_kill(params.get("name") or params.get("pid"))
            elif action == "app_close":
                return await self._app_close(params.get("name"))
            elif action == "app_kill":
                return await self._app_kill(params.get("name"))
            
            # ==================== 应用程序控制 ====================
            elif action == "app_open":
                return await self._app_open(params.get("name") or params.get("path"))
            elif action == "app_list":
                return await self._app_list()
            
            # ==================== 窗口管理 ====================
            elif action == "window_minimize":
                return await self._window_minimize()
            elif action == "window_maximize":
                return await self._window_maximize()
            elif action == "window_close":
                return await self._window_close()
            
            # ==================== 剪贴板 ====================
            elif action == "clipboard_get":
                return await self._clipboard_get()
            elif action == "clipboard_set":
                return await self._clipboard_set(params.get("text", ""))
            elif action == "clipboard_write":
                return await self._clipboard_set(params.get("text", ""))
            elif action == "clipboard_clear":
                return await self._clipboard_clear()
            
            # ==================== 服务管理 ====================
            elif action == "service_list":
                return await self._service_list(params.get("filter"))
            elif action == "service_start":
                return await self._service_start(params.get("name"))
            elif action == "service_stop":
                return await self._service_stop(params.get("name"))
            elif action == "service_restart":
                return await self._service_restart(params.get("name"))
            
            # ==================== 系统设置 ====================
            elif action == "wallpaper_get":
                return await self._wallpaper_get()
            elif action == "wallpaper_set":
                return await self._wallpaper_set(params.get("path"))
            elif action == "brightness_get":
                return await self._brightness_get()
            elif action == "brightness_set":
                return await self._brightness_set(params.get("level", 50))
            elif action == "brightness_up":
                return await self._brightness_up()
            elif action == "brightness_down":
                return await self._brightness_down()
            
            # ==================== 显示器控制 ====================
            elif action == "monitor_off":
                return await self._monitor_off()
            elif action == "display_output":
                return await self._switch_display_output(params.get("output", "internal"))
            
            # ==================== 音频设备控制 ====================
            elif action in ("audio_list", "audio_device_control"):
                operation = params.get("operation", "list")
                if operation == "list":
                    return await self._list_audio_devices()
                elif operation == "switch_output":
                    return await self._switch_audio_output(params.get("device"))
                elif operation == "switch_input":
                    return await self._switch_audio_input(params.get("device"))
                elif operation == "default_output":
                    return await self._set_default_audio_output(params.get("device"))
                elif operation == "default_input":
                    return await self._set_default_audio_input(params.get("device"))
                else:
                    return await self._list_audio_devices()
            elif action == "audio_output":
                return await self._switch_audio_output(params.get("device"))
            elif action == "audio_output_switch":
                return await self._switch_audio_output(params.get("device"))
            elif action == "audio_input_switch":
                return await self._switch_audio_input(params.get("device"))
            elif action == "audio_output_default":
                return await self._set_default_audio_output(params.get("device"))
            elif action == "audio_input_default":
                return await self._set_default_audio_input(params.get("device"))
            
            # ==================== 时间日期 ====================
            elif action == "time_now":
                return self._time_now()
            elif action == "date_today":
                return self._date_today()
            
            # ==================== 清理维护 ====================
            elif action == "clean_temp":
                return await self._clean_temp()
            elif action == "empty_recycle":
                result = await self._empty_recycle(confirm=params.get("confirm", False))
                if result == "CONFIRM_EMPTY_RECYCLE":
                    return "⚠️ 清空回收站将永久删除所有文件，无法恢复！\n\n确认要清空回收站吗？请回复\"确认\"或\"取消\"。"
                return result
            
            # ==================== 通知 ====================
            elif action == "notification":
                return await self._send_notification(
                    params.get("title", "提醒"),
                    params.get("message", params.get("text", ""))
                )
            
            else:
                result = f"❌ 未知的操作: {action}\n\n{self._get_help()}"

        except Exception as e:
            logger.error(f"OS Agent 执行失败: {e}")
            result = f"❌ 操作失败: {str(e)}"
        
        if result and ("❌" in result or "未找到" in result or "不存在" in result):
            task.no_retry = True
        return result
    
    def _parse_general_action(self, text: str) -> str:
        """解析 general 类型任务的意图"""
        text_lower = text.lower()
        
        time_keywords = ["几点", "时间", "现在几点"]
        if any(kw in text_lower for kw in time_keywords):
            return "time_now"
        
        date_keywords = ["几号", "日期", "今天日期", "今天几号"]
        if any(kw in text_lower for kw in date_keywords):
            return "date_today"
        
        volume_keywords = ["音量", "声音"]
        if any(kw in text_lower for kw in volume_keywords):
            if "大" in text_lower or "高" in text_lower:
                return "volume_up"
            elif "小" in text_lower or "低" in text_lower:
                return "volume_down"
            elif "静音" in text_lower or "关掉声音" in text_lower:
                return "volume_mute"
            return "volume_get"
        
        screenshot_keywords = ["截图", "截屏", "抓屏"]
        if any(kw in text_lower for kw in screenshot_keywords):
            return "screenshot"
        
        power_keywords = {
            "关机": "shutdown",
            "重启": "restart",
            "注销": "logout",
            "锁屏": "lock",
            "休眠": "sleep",
        }
        for kw, action in power_keywords.items():
            if kw in text_lower:
                return action
        
        brightness_keywords = ["亮度", "屏幕亮度"]
        if any(kw in text_lower for kw in brightness_keywords):
            if "亮" in text_lower or "高" in text_lower:
                return "brightness_up"
            elif "暗" in text_lower or "低" in text_lower:
                return "brightness_down"
            return "brightness_get"
        
        audio_device_keywords = ["音频设备", "声音设备", "音频", "扬声器", "麦克风", "输出设备", "输入设备"]
        if any(kw in text_lower for kw in audio_device_keywords):
            if "切换" in text_lower or "换" in text_lower:
                if "输出" in text_lower or "扬声器" in text_lower:
                    return "audio_output_switch"
                elif "输入" in text_lower or "麦克风" in text_lower:
                    return "audio_input_switch"
            return "audio_list"
        
        system_keywords = ["系统信息", "cpu", "内存", "磁盘"]
        if any(kw in text_lower for kw in system_keywords):
            return "system_info"
        
        return "help"
    
    def _get_help(self) -> str:
        """获取帮助信息"""
        return """🖥️ 系统智能体支持的操作：

📌 音量控制：
• 静音 / 取消静音 - 系统静音控制
• 声音大一点 / 声音小一点 - 调节音量
• 音量 - 查看当前音量

📌 音频设备：
• 音频设备 / 声音设备 - 列出所有音频设备
• 切换音频输出 [设备名] - 切换扬声器
• 切换音频输入 [设备名] - 切换麦克风

📌 系统电源：
• 关机 / 重启 / 注销 / 锁屏 / 休眠

📌 显示器：
• 截图 / 截屏 - 截取屏幕
• 关闭显示器 / 息屏
• 亮度 / 调亮 / 调暗

📌 网络状态：
• WiFi状态 / 网络状态
• 蓝牙状态 / 电池状态

📌 系统信息：
• 系统信息 / CPU / 内存 / 磁盘

📌 进程管理：
• 进程列表 / 运行中的程序
• 关闭程序 [名称] / 强制关闭 [名称]

📌 应用程序：
• 打开 [程序名] - 如：打开记事本
• 关闭程序 [程序名]

📌 窗口管理：
• 最小化 / 最大化 / 关闭窗口

📌 剪贴板：
• 剪贴板 - 查看剪贴板内容

📌 服务管理：
• 服务列表 / 启动服务 / 停止服务

📌 系统设置：
• 壁纸 / 换壁纸 [路径]

📌 清理维护：
• 清理垃圾 / 清空回收站

📌 其他：
• 现在几点 / 今天日期
• 通知 [内容] - 发送系统通知"""

    async def _run_command(self, command: str, shell: bool = True) -> tuple:
        """运行系统命令"""
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            return (
                process.returncode,
                stdout.decode('utf-8', errors='ignore').strip(),
                stderr.decode('utf-8', errors='ignore').strip()
            )
        except Exception as e:
            return (-1, "", str(e))

    async def _run_powershell(self, script: str) -> tuple:
        """运行 PowerShell 脚本"""
        import base64
        script_bytes = script.encode('utf-16le')
        encoded_script = base64.b64encode(script_bytes).decode('ascii')
        cmd = f'powershell -EncodedCommand {encoded_script}'
        return await self._run_command(cmd)

    # ==================== 音量控制 ====================
    async def _set_volume(self, level: int) -> str:
        """设置音量 (0-100)"""
        level = max(0, min(100, level))
        
        if self.system == "Windows":
            ps_script = f'''
            Add-Type -TypeDefinition @"
            using System;
            using System.Runtime.InteropServices;
            [Guid("5CDF2C82-841E-4546-9722-0CF74078229A"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
            interface IAudioEndpointVolume {{
                int f(); int g(); int h(); int i();
                int SetMasterVolumeLevelScalar(float fLevel, IntPtr pguidEventContext);
                int j();
                int GetMasterVolumeLevelScalar(out float pfLevel);
                int k(); int l(); int m(); int n();
            }}
            [Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
            interface IMMDevice {{
                int Activate(ref Guid iid, int dwClsCtx, IntPtr pActivationParams, out IAudioEndpointVolume aev);
            }}
            [Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
            interface IMMDeviceEnumerator {{
                int f();
                int GetDefaultAudioEndpoint(int dataFlow, int role, out IMMDevice endpoint);
            }}
            [ComImport, Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")]
            class MMDeviceEnumerator {{ }}
            public class Volume {{
                static IAudioEndpointVolume Vol() {{
                    var enumerator = new MMDeviceEnumerator() as IMMDeviceEnumerator;
                    IMMDevice dev;
                    enumerator.GetDefaultAudioEndpoint(0, 1, out dev);
                    IAudioEndpointVolume epv;
                    var guid = typeof(IAudioEndpointVolume).GUID;
                    dev.Activate(ref guid, 0, IntPtr.Zero, out epv);
                    return epv;
                }}
                public static void SetVolume(int level) {{
                    Vol().SetMasterVolumeLevelScalar(level / 100f, IntPtr.Zero);
                }}
            }}
            "@
            [Volume]::SetVolume({level})
            '''
            return_code, stdout, stderr = await self._run_powershell(ps_script)
            if return_code == 0:
                return f"✅ 音量已设置为 {level}%"
            return f"❌ 设置音量失败: {stderr}"
        return "❌ 暂不支持此操作系统"

    async def _get_volume(self) -> str:
        """获取当前音量"""
        if self.system == "Windows":
            ps_script = '''
            Add-Type -TypeDefinition @"
            using System;
            using System.Runtime.InteropServices;
            [Guid("5CDF2C82-841E-4546-9722-0CF74078229A"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
            interface IAudioEndpointVolume {
                int f(); int g(); int h(); int i();
                int SetMasterVolumeLevelScalar(float fLevel, IntPtr pguidEventContext);
                int j();
                int GetMasterVolumeLevelScalar(out float pfLevel);
                int k(); int l(); int m(); int n();
            }
            [Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
            interface IMMDevice {
                int Activate(ref Guid iid, int dwClsCtx, IntPtr pActivationParams, out IAudioEndpointVolume aev);
            }
            [Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
            interface IMMDeviceEnumerator {
                int f();
                int GetDefaultAudioEndpoint(int dataFlow, int role, out IMMDevice endpoint);
            }
            [ComImport, Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")]
            class MMDeviceEnumerator { }
            public class Volume {
                static IAudioEndpointVolume Vol() {
                    var enumerator = new MMDeviceEnumerator() as IMMDeviceEnumerator;
                    IMMDevice dev;
                    enumerator.GetDefaultAudioEndpoint(0, 1, out dev);
                    IAudioEndpointVolume epv;
                    var guid = typeof(IAudioEndpointVolume).GUID;
                    dev.Activate(ref guid, 0, IntPtr.Zero, out epv);
                    return epv;
                }
                public static int GetVolume() {
                    float level;
                    Vol().GetMasterVolumeLevelScalar(out level);
                    return (int)(level * 100);
                }
            }
            "@
            [Volume]::GetVolume()
            '''
            return_code, stdout, stderr = await self._run_powershell(ps_script)
            if return_code == 0 and stdout:
                return f"🔊 当前音量: {stdout}%"
        return "❌ 无法获取音量"

    async def _mute_volume(self) -> str:
        """静音"""
        if self.system == "Windows":
            try:
                VK_VOLUME_MUTE = 0xAD
                KEYEVENTF_EXTENDEDKEY = 0x0001
                KEYEVENTF_KEYUP = 0x0002
                ctypes.windll.user32.keybd_event(VK_VOLUME_MUTE, 0, KEYEVENTF_EXTENDEDKEY, 0)
                ctypes.windll.user32.keybd_event(VK_VOLUME_MUTE, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
                return "🔇 已静音"
            except Exception as e:
                logger.error(f"静音失败: {e}")
        return "❌ 静音失败"

    async def _unmute_volume(self) -> str:
        """取消静音"""
        if self.system == "Windows":
            try:
                VK_VOLUME_MUTE = 0xAD
                KEYEVENTF_EXTENDEDKEY = 0x0001
                KEYEVENTF_KEYUP = 0x0002
                ctypes.windll.user32.keybd_event(VK_VOLUME_MUTE, 0, KEYEVENTF_EXTENDEDKEY, 0)
                ctypes.windll.user32.keybd_event(VK_VOLUME_MUTE, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
                return "🔊 已取消静音"
            except Exception as e:
                logger.error(f"取消静音失败: {e}")
        return "❌ 取消静音失败"

    async def _volume_up(self) -> str:
        """增加音量"""
        if self.system == "Windows":
            try:
                VK_VOLUME_UP = 0xAF
                KEYEVENTF_EXTENDEDKEY = 0x0001
                KEYEVENTF_KEYUP = 0x0002
                ctypes.windll.user32.keybd_event(VK_VOLUME_UP, 0, KEYEVENTF_EXTENDEDKEY, 0)
                ctypes.windll.user32.keybd_event(VK_VOLUME_UP, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
                return "🔊 音量已增加"
            except Exception as e:
                logger.error(f"增加音量失败: {e}")
        return "❌ 增加音量失败"

    async def _volume_down(self) -> str:
        """降低音量"""
        if self.system == "Windows":
            try:
                VK_VOLUME_DOWN = 0xAE
                KEYEVENTF_EXTENDEDKEY = 0x0001
                KEYEVENTF_KEYUP = 0x0002
                ctypes.windll.user32.keybd_event(VK_VOLUME_DOWN, 0, KEYEVENTF_EXTENDEDKEY, 0)
                ctypes.windll.user32.keybd_event(VK_VOLUME_DOWN, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
                return "🔊 音量已降低"
            except Exception as e:
                logger.error(f"降低音量失败: {e}")
        return "❌ 降低音量失败"

    # ==================== 系统电源控制 ====================
    async def _lock_screen(self) -> str:
        """锁屏"""
        if self.system == "Windows":
            try:
                ctypes.windll.user32.LockWorkStation()
                return "🔒 屏幕已锁定"
            except Exception as e:
                logger.error(f"锁屏失败: {e}")
        return "❌ 锁屏失败"

    async def _logout(self) -> str:
        """注销"""
        if self.system == "Windows":
            try:
                ctypes.windll.user32.ExitWindowsEx(0, 0)
                return "👋 正在注销..."
            except Exception as e:
                logger.error(f"注销失败: {e}")
        return "❌ 注销失败"

    async def _screenshot(self, save_to_file: bool = True) -> str:
        """截图"""
        if self.system == "Windows":
            try:
                import os
                from datetime import datetime
                
                desktop = os.path.join(os.path.expanduser("~"), "Desktop")
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"screenshot_{timestamp}.png"
                filepath = os.path.join(desktop, filename)
                
                cmd = f'''powershell -Command "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Screen]::PrimaryScreen.Bounds; $bitmap = New-Object System.Drawing.Bitmap([System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Width, [System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Height); $graphics = [System.Drawing.Graphics]::FromImage($bitmap); $graphics.CopyFromScreen([System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Location, [System.Drawing.Point]::Empty, [System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Size); $bitmap.Save('{filepath}'); $graphics.Dispose(); $bitmap.Dispose()"'''
                
                return_code, stdout, stderr = await self._run_command(cmd)
                
                if return_code == 0 and os.path.exists(filepath):
                    return f"📸 截图已保存到: {filepath}"
                else:
                    VK_SNAPSHOT = 0x2C
                    KEYEVENTF_EXTENDEDKEY = 0x0001
                    KEYEVENTF_KEYUP = 0x0002
                    ctypes.windll.user32.keybd_event(VK_SNAPSHOT, 0, KEYEVENTF_EXTENDEDKEY, 0)
                    ctypes.windll.user32.keybd_event(VK_SNAPSHOT, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
                    return "📸 截图已保存到剪贴板"
            except Exception as e:
                logger.error(f"截图失败: {e}")
        return "❌ 截图失败"

    async def _screen_record(self) -> str:
        """录屏"""
        return "📹 录屏功能暂未实现，请使用 Win+G 打开游戏录制工具"

    async def _sleep_system(self) -> str:
        """系统睡眠"""
        if self.system == "Windows":
            cmd = "rundll32.exe powrprof.dll,SetSuspendState 0,1,0"
            return_code, stdout, stderr = await self._run_command(cmd)
            if return_code == 0:
                return "💤 系统已进入睡眠模式"
        return "❌ 睡眠命令执行失败"

    async def _shutdown_system(self) -> str:
        """系统关机"""
        if self.system == "Windows":
            cmd = "shutdown /s /t 60"
            return_code, stdout, stderr = await self._run_command(cmd)
            if return_code == 0:
                return "🔌 系统将在60秒后关机（运行 shutdown /a 取消）"
        return "❌ 关机命令执行失败"

    async def _restart_system(self) -> str:
        """系统重启"""
        if self.system == "Windows":
            cmd = "shutdown /r /t 60"
            return_code, stdout, stderr = await self._run_command(cmd)
            if return_code == 0:
                return "🔄 系统将在60秒后重启（运行 shutdown /a 取消）"
        return "❌ 重启命令执行失败"

    # ==================== WiFi 控制 ====================
    async def _list_wifi(self) -> str:
        """列出可用WiFi网络"""
        if self.system == "Windows":
            cmd = "netsh wlan show networks mode=bssid"
            return_code, stdout, stderr = await self._run_command(cmd)
            if return_code == 0:
                networks = []
                for line in stdout.split('\n'):
                    if 'SSID' in line and ':' in line:
                        ssid = line.split(':', 1)[1].strip()
                        if ssid:
                            networks.append(ssid)
                if networks:
                    return "📶 可用WiFi网络:\n" + '\n'.join(f"  • {n}" for n in networks[:10])
                else:
                    return "📶 未找到WiFi网络"
        return "❌ 无法获取WiFi列表"

    async def _connect_wifi(self, ssid: Optional[str], password: Optional[str]) -> str:
        """连接WiFi"""
        if not ssid:
            return "❌ 请提供WiFi名称(SSID)"
        
        if self.system == "Windows":
            profile_xml = f'''<?xml version="1.0"?>
            <WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
                <name>{ssid}</name>
                <SSIDConfig>
                    <SSID>
                        <name>{ssid}</name>
                    </SSID>
                </SSIDConfig>
                <connectionType>ESS</connectionType>
                <connectionMode>auto</connectionMode>
                <MSM>
                    <security>
                        <authEncryption>
                            <authentication>WPA2PSK</authentication>
                            <encryption>AES</encryption>
                            <useOneX>false</useOneX>
                        </authEncryption>
                        <sharedKey>
                            <keyType>passPhrase</keyType>
                            <protected>false</protected>
                            <keyMaterial>{password}</keyMaterial>
                        </sharedKey>
                    </security>
                </MSM>
            </WLANProfile>'''
            
            profile_path = os.path.join(os.environ['TEMP'], 'wifi_profile.xml')
            with open(profile_path, 'w', encoding='utf-8') as f:
                f.write(profile_xml)
            
            cmd = f'netsh wlan add profile filename="{profile_path}"'
            return_code, stdout, stderr = await self._run_command(cmd)
            
            if return_code == 0:
                cmd = f'netsh wlan connect name="{ssid}"'
                return_code, stdout, stderr = await self._run_command(cmd)
                if return_code == 0:
                    return f"✅ 已连接到 {ssid}"
            
            return f"❌ 连接WiFi失败: {stderr}"
        return "❌ 暂不支持此操作系统"

    async def _disconnect_wifi(self) -> str:
        """断开WiFi"""
        if self.system == "Windows":
            cmd = "netsh wlan disconnect"
            return_code, stdout, stderr = await self._run_command(cmd)
            if return_code == 0:
                return "📶 WiFi已断开"
        return "❌ 断开WiFi失败"

    async def _wifi_status(self) -> str:
        """WiFi状态"""
        if self.system == "Windows":
            cmd = "netsh wlan show interfaces"
            return_code, stdout, stderr = await self._run_command(cmd)
            if return_code == 0:
                info = []
                for line in stdout.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        key = key.strip()
                        value = value.strip()
                        if key in ['SSID', '状态', '信号', '接收速率', '传输速率']:
                            info.append(f"  • {key}: {value}")
                if info:
                    return "📶 WiFi状态:\n" + '\n'.join(info)
                else:
                    return "📶 WiFi未连接"
        return "❌ 无法获取WiFi状态"

    async def _network_info(self) -> str:
        """网络信息"""
        if self.system == "Windows":
            ps_script = '''
            Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notlike "*Loopback*" } | 
            Select-Object InterfaceAlias, IPAddress, PrefixLength | Format-Table -AutoSize
            '''
            return_code, stdout, stderr = await self._run_powershell(ps_script)
            if return_code == 0:
                return f"🌐 网络信息:\n{stdout}"
        return "❌ 无法获取网络信息"

    async def _bluetooth_status(self) -> str:
        """蓝牙状态"""
        if self.system == "Windows":
            ps_script = '''
            Get-Service bthserv | Select-Object Name, Status, StartType | Format-Table -AutoSize
            '''
            return_code, stdout, stderr = await self._run_powershell(ps_script)
            if return_code == 0:
                return f"📡 蓝牙服务状态:\n{stdout}"
        return "❌ 无法获取蓝牙状态"

    async def _battery_status(self) -> str:
        """电池状态"""
        if self.system == "Windows":
            ps_script = '''
            $battery = Get-WmiObject Win32_Battery
            if ($battery) {
                "电量: " + $battery.EstimatedChargeRemaining + "%"
                "状态: " + $battery.BatteryStatus
            } else {
                "未检测到电池"
            }
            '''
            return_code, stdout, stderr = await self._run_powershell(ps_script)
            if return_code == 0:
                return f"🔋 电池状态:\n{stdout}"
        return "❌ 无法获取电池状态"

    # ==================== 系统信息 ====================
    async def _system_info(self) -> str:
        """系统信息"""
        if self.system == "Windows":
            ps_script = '''
            $os = Get-CimInstance Win32_OperatingSystem
            $cpu = Get-CimInstance Win32_Processor
            $ram = Get-CimInstance Win32_ComputerSystem
            
            "操作系统: " + $os.Caption + " " + $os.Version
            "计算机名: " + $env:COMPUTERNAME
            "用户名: " + $env:USERNAME
            "CPU: " + $cpu.Name
            "内存: " + [math]::Round($ram.TotalPhysicalMemory / 1GB, 2) + " GB"
            "系统启动时间: " + $os.LastBootUpTime
            '''
            return_code, stdout, stderr = await self._run_powershell(ps_script)
            if return_code == 0:
                return f"💻 系统信息:\n{stdout}"
        return "❌ 无法获取系统信息"

    async def _cpu_info(self) -> str:
        """CPU信息"""
        if self.system == "Windows":
            ps_script = '''
            $cpu = Get-CimInstance Win32_Processor
            "CPU: " + $cpu.Name
            "核心数: " + $cpu.NumberOfCores
            "线程数: " + $cpu.NumberOfLogicalProcessors
            "最大频率: " + $cpu.MaxClockSpeed + " MHz"
            
            $load = Get-WmiObject Win32_Processor | Measure-Object -Property LoadPercentage -Average
            "当前使用率: " + [math]::Round($load.Average, 1) + "%"
            '''
            return_code, stdout, stderr = await self._run_powershell(ps_script)
            if return_code == 0:
                return f"🖥️ CPU信息:\n{stdout}"
        return "❌ 无法获取CPU信息"

    async def _memory_info(self) -> str:
        """内存信息"""
        if self.system == "Windows":
            ps_script = '''
            $os = Get-CimInstance Win32_OperatingSystem
            $total = [math]::Round($os.TotalVisibleMemorySize / 1MB, 2)
            $free = [math]::Round($os.FreePhysicalMemory / 1MB, 2)
            $used = $total - $free
            $percent = [math]::Round(($used / $total) * 100, 1)
            
            "总内存: " + $total + " GB"
            "已使用: " + [math]::Round($used, 2) + " GB"
            "可用: " + $free + " GB"
            "使用率: " + $percent + "%"
            '''
            return_code, stdout, stderr = await self._run_powershell(ps_script)
            if return_code == 0:
                return f"🧠 内存信息:\n{stdout}"
        return "❌ 无法获取内存信息"

    async def _disk_info(self) -> str:
        """磁盘信息"""
        if self.system == "Windows":
            ps_script = '''
            Get-CimInstance Win32_LogicalDisk | Where-Object { $_.DriveType -eq 3 } | ForEach-Object {
                $total = [math]::Round($_.Size / 1GB, 2)
                $free = [math]::Round($_.FreeSpace / 1GB, 2)
                $used = $total - $free
                $percent = [math]::Round(($used / $total) * 100, 1)
                "磁盘 " + $_.DeviceID + " (" + $_.VolumeName + ")"
                "  总容量: " + $total + " GB"
                "  已使用: " + [math]::Round($used, 2) + " GB (" + $percent + "%)"
                "  可用: " + $free + " GB"
                ""
            }
            '''
            return_code, stdout, stderr = await self._run_powershell(ps_script)
            if return_code == 0:
                return f"💾 磁盘信息:\n{stdout}"
        return "❌ 无法获取磁盘信息"

    # ==================== 进程管理 ====================
    async def _process_list(self, filter_name: Optional[str] = None) -> str:
        """进程列表"""
        if self.system == "Windows":
            if filter_name:
                ps_script = f'''
                Get-Process | Where-Object {{ $_.ProcessName -like "*{filter_name}*" }} | 
                Select-Object Id, ProcessName, CPU, WorkingSet64 | 
                Sort-Object WorkingSet64 -Descending | 
                Select-Object -First 20 | 
                Format-Table -AutoSize
                '''
            else:
                ps_script = '''
                Get-Process | 
                Select-Object Id, ProcessName, CPU, WorkingSet64 | 
                Sort-Object WorkingSet64 -Descending | 
                Select-Object -First 30 | 
                Format-Table -AutoSize
                '''
            return_code, stdout, stderr = await self._run_powershell(ps_script)
            if return_code == 0:
                return f"📋 进程列表:\n{stdout}"
        return "❌ 无法获取进程列表"

    async def _process_kill(self, name_or_pid: Optional[str]) -> str:
        """结束进程"""
        if not name_or_pid:
            return "❌ 请提供进程名称或PID"
        
        if self.system == "Windows":
            if name_or_pid.isdigit():
                cmd = f"taskkill /F /PID {name_or_pid}"
            else:
                cmd = f"taskkill /F /IM {name_or_pid}.exe"
            
            return_code, stdout, stderr = await self._run_command(cmd)
            if return_code == 0:
                return f"✅ 已结束进程: {name_or_pid}"
            return f"❌ 结束进程失败: {stderr}"
        return "❌ 暂不支持此操作系统"

    async def _app_close(self, name: Optional[str]) -> str:
        """关闭应用程序"""
        if not name:
            return "❌ 请提供程序名称"
        return await self._process_kill(name)

    async def _app_kill(self, name: Optional[str]) -> str:
        """强制关闭应用程序"""
        if not name:
            return "❌ 请提供程序名称"
        return await self._process_kill(name)

    # ==================== 应用程序控制 ====================
    async def _app_open(self, name_or_path: Optional[str]) -> str:
        """打开应用程序"""
        if not name_or_path:
            return "❌ 请提供程序名称或路径"
        
        if self.system == "Windows":
            common_apps = {
                "记事本": "notepad",
                "计算器": "calc",
                "画图": "mspaint",
                "记事本": "notepad",
                "资源管理器": "explorer",
                "控制面板": "control",
                "命令提示符": "cmd",
                "powershell": "powershell",
                "设置": "ms-settings:",
                "浏览器": "start msedge",
                "edge": "msedge",
                "chrome": "chrome",
                "word": "winword",
                "excel": "excel",
                "powerpoint": "powerpnt",
                "outlook": "outlook",
                "微信": "WeChat",
                "qq": "QQ",
                "音乐": "wmplayer",
                "媒体播放器": "wmplayer",
                "照片": "ms-photos:",
                "日历": "outlookcal:",
                "邮件": "mailto:",
                "录音机": "soundrecorder",
                "任务管理器": "taskmgr",
                "注册表": "regedit",
                "组策略": "gpedit.msc",
                "服务": "services.msc",
                "事件查看器": "eventvwr",
                "设备管理器": "devmgmt.msc",
                "磁盘管理": "diskmgmt.msc",
            }
            
            app_cmd = common_apps.get(name_or_path.lower(), name_or_path)
            
            if os.path.isfile(app_cmd):
                cmd = f'start "" "{app_cmd}"'
            else:
                cmd = f'start {app_cmd}'
            
            return_code, stdout, stderr = await self._run_command(cmd)
            if return_code == 0:
                return f"✅ 已启动: {name_or_path}"
            return f"❌ 启动失败: {stderr}"
        return "❌ 暂不支持此操作系统"

    async def _app_list(self) -> str:
        """列出常用应用程序"""
        apps = """📱 常用应用程序:
• 记事本 / 计算器 / 画图
• 资源管理器 / 控制面板 / 设置
• 浏览器 / Edge / Chrome
• Word / Excel / PowerPoint / Outlook
• 微信 / QQ
• 任务管理器 / 设备管理器
• 服务 / 注册表 / 组策略

使用方法: 打开 [程序名]"""
        return apps

    # ==================== 窗口管理 ====================
    async def _window_minimize(self) -> str:
        """最小化当前窗口"""
        if self.system == "Windows":
            try:
                VK_LWIN = 0x5B
                VK_DOWN = 0x28
                KEYEVENTF_EXTENDEDKEY = 0x0001
                KEYEVENTF_KEYUP = 0x0002
                
                ctypes.windll.user32.keybd_event(VK_LWIN, 0, KEYEVENTF_EXTENDEDKEY, 0)
                ctypes.windll.user32.keybd_event(VK_DOWN, 0, KEYEVENTF_EXTENDEDKEY, 0)
                ctypes.windll.user32.keybd_event(VK_DOWN, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
                ctypes.windll.user32.keybd_event(VK_LWIN, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
                return "✅ 已最小化当前窗口"
            except Exception as e:
                logger.error(f"最小化失败: {e}")
        return "❌ 最小化失败"

    async def _window_maximize(self) -> str:
        """最大化当前窗口"""
        if self.system == "Windows":
            try:
                VK_LWIN = 0x5B
                VK_UP = 0x26
                KEYEVENTF_EXTENDEDKEY = 0x0001
                KEYEVENTF_KEYUP = 0x0002
                
                ctypes.windll.user32.keybd_event(VK_LWIN, 0, KEYEVENTF_EXTENDEDKEY, 0)
                ctypes.windll.user32.keybd_event(VK_UP, 0, KEYEVENTF_EXTENDEDKEY, 0)
                ctypes.windll.user32.keybd_event(VK_UP, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
                ctypes.windll.user32.keybd_event(VK_LWIN, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
                return "✅ 已最大化当前窗口"
            except Exception as e:
                logger.error(f"最大化失败: {e}")
        return "❌ 最大化失败"

    async def _window_close(self) -> str:
        """关闭当前窗口"""
        if self.system == "Windows":
            try:
                VK_MENU = 0x12
                VK_F4 = 0x73
                KEYEVENTF_EXTENDEDKEY = 0x0001
                KEYEVENTF_KEYUP = 0x0002
                
                ctypes.windll.user32.keybd_event(VK_MENU, 0, KEYEVENTF_EXTENDEDKEY, 0)
                ctypes.windll.user32.keybd_event(VK_F4, 0, KEYEVENTF_EXTENDEDKEY, 0)
                ctypes.windll.user32.keybd_event(VK_F4, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
                ctypes.windll.user32.keybd_event(VK_MENU, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
                return "✅ 已关闭当前窗口"
            except Exception as e:
                logger.error(f"关闭窗口失败: {e}")
        return "❌ 关闭窗口失败"

    # ==================== 剪贴板 ====================
    async def _clipboard_get(self) -> str:
        """获取剪贴板内容"""
        if self.system == "Windows":
            ps_script = '''
            Add-Type -AssemblyName System.Windows.Forms
            [System.Windows.Forms.Clipboard]::GetText()
            '''
            return_code, stdout, stderr = await self._run_powershell(ps_script)
            if return_code == 0:
                if stdout:
                    return f"📋 剪贴板内容:\n{stdout[:500]}{'...' if len(stdout) > 500 else ''}"
                return "📋 剪贴板为空"
        return "❌ 无法获取剪贴板内容"

    async def _clipboard_set(self, text: str) -> str:
        """设置剪贴板内容"""
        if self.system == "Windows":
            ps_script = f'''
            Add-Type -AssemblyName System.Windows.Forms
            [System.Windows.Forms.Clipboard]::SetText("{text}")
            '''
            return_code, stdout, stderr = await self._run_powershell(ps_script)
            if return_code == 0:
                return f"✅ 已复制到剪贴板: {text[:50]}{'...' if len(text) > 50 else ''}"
        return "❌ 设置剪贴板失败"

    async def _clipboard_clear(self) -> str:
        """清空剪贴板"""
        if self.system == "Windows":
            ps_script = '''
            Add-Type -AssemblyName System.Windows.Forms
            [System.Windows.Forms.Clipboard]::Clear()
            '''
            return_code, stdout, stderr = await self._run_powershell(ps_script)
            if return_code == 0:
                return "✅ 剪贴板已清空"
        return "❌ 清空剪贴板失败"

    # ==================== 服务管理 ====================
    async def _service_list(self, filter_name: Optional[str] = None) -> str:
        """服务列表"""
        if self.system == "Windows":
            if filter_name:
                ps_script = f'''
                Get-Service | Where-Object {{ $_.Name -like "*{filter_name}*" -or $_.DisplayName -like "*{filter_name}*" }} | 
                Select-Object Name, Status, StartType, DisplayName | 
                Format-Table -AutoSize -Wrap
                '''
            else:
                ps_script = '''
                Get-Service | Where-Object { $_.Status -eq "Running" } | 
                Select-Object Name, Status, DisplayName | 
                Format-Table -AutoSize -Wrap
                '''
            return_code, stdout, stderr = await self._run_powershell(ps_script)
            if return_code == 0:
                return f"⚙️ 服务列表:\n{stdout}"
        return "❌ 无法获取服务列表"

    async def _service_start(self, name: Optional[str]) -> str:
        """启动服务"""
        if not name:
            return "❌ 请提供服务名称"
        
        if self.system == "Windows":
            cmd = f'net start "{name}"'
            return_code, stdout, stderr = await self._run_command(cmd)
            if return_code == 0:
                return f"✅ 服务 {name} 已启动"
            return f"❌ 启动服务失败: {stderr}"
        return "❌ 暂不支持此操作系统"

    async def _service_stop(self, name: Optional[str]) -> str:
        """停止服务"""
        if not name:
            return "❌ 请提供服务名称"
        
        if self.system == "Windows":
            cmd = f'net stop "{name}"'
            return_code, stdout, stderr = await self._run_command(cmd)
            if return_code == 0:
                return f"✅ 服务 {name} 已停止"
            return f"❌ 停止服务失败: {stderr}"
        return "❌ 暂不支持此操作系统"

    async def _service_restart(self, name: Optional[str]) -> str:
        """重启服务"""
        if not name:
            return "❌ 请提供服务名称"
        
        await self._service_stop(name)
        await asyncio.sleep(1)
        return await self._service_start(name)

    # ==================== 系统设置 ====================
    async def _wallpaper_get(self) -> str:
        """获取当前壁纸"""
        if self.system == "Windows":
            ps_script = '''
            Add-Type @"
            using System;
            using System.Runtime.InteropServices;
            public class Wallpaper {
                [DllImport("user32.dll", CharSet=CharSet.Auto)]
                public static extern int SystemParametersInfo(int uAction, int uParam, string lpvParam, int fuWinIni);
            }
            "@
            $path = [Environment]::GetFolderPath("MyPictures") + "\\wallpaper.bmp"
            [Wallpaper]::SystemParametersInfo(0x0073, 0, $path, 0)
            $path
            '''
            return_code, stdout, stderr = await self._run_powershell(ps_script)
            if return_code == 0:
                return f"🖼️ 当前壁纸路径: {stdout}"
        return "❌ 无法获取壁纸信息"

    async def _wallpaper_set(self, path: Optional[str]) -> str:
        """设置壁纸"""
        if not path:
            return "❌ 请提供壁纸路径"
        
        if not os.path.exists(path):
            return f"❌ 文件不存在: {path}"
        
        if self.system == "Windows":
            ps_script = f'''
            Add-Type @"
            using System;
            using System.Runtime.InteropServices;
            public class Wallpaper {{
                [DllImport("user32.dll", CharSet=CharSet.Auto)]
                public static extern int SystemParametersInfo(int uAction, int uParam, string lpvParam, int fuWinIni);
            }}
            "@
            [Wallpaper]::SystemParametersInfo(0x0014, 0, "{path}", 3)
            '''
            return_code, stdout, stderr = await self._run_powershell(ps_script)
            if return_code == 0:
                return f"✅ 壁纸已更换: {path}"
        return "❌ 设置壁纸失败"

    async def _brightness_get(self) -> str:
        """获取屏幕亮度"""
        if self.system == "Windows":
            ps_script = '''
            Get-CimInstance -Namespace root/wmi -ClassName WmiMonitorBrightness | 
            Select-Object CurrentBrightness, InstanceName
            '''
            return_code, stdout, stderr = await self._run_powershell(ps_script)
            if return_code == 0:
                return f"☀️ 屏幕亮度:\n{stdout}"
        return "❌ 无法获取亮度信息"

    async def _brightness_set(self, level: int) -> str:
        """设置屏幕亮度"""
        level = max(0, min(100, level))
        
        if self.system == "Windows":
            ps_script = f'''
            $monitor = Get-CimInstance -Namespace root/wmi -ClassName WmiMonitorBrightnessMethods
            $monitor | Invoke-CimMethod -MethodName WmiSetBrightness -Arguments @{{Brightness={level}; Timeout=0}}
            '''
            return_code, stdout, stderr = await self._run_powershell(ps_script)
            if return_code == 0:
                return f"✅ 屏幕亮度已设置为 {level}%"
        return "❌ 设置亮度失败"

    async def _brightness_up(self) -> str:
        """增加亮度"""
        if self.system == "Windows":
            ps_script = '''
            $current = (Get-CimInstance -Namespace root/wmi -ClassName WmiMonitorBrightness).CurrentBrightness
            $new = [Math]::Min($current + 10, 100)
            $monitor = Get-CimInstance -Namespace root/wmi -ClassName WmiMonitorBrightnessMethods
            $monitor | Invoke-CimMethod -MethodName WmiSetBrightness -Arguments @{Brightness=$new; Timeout=0}
            $new
            '''
            return_code, stdout, stderr = await self._run_powershell(ps_script)
            if return_code == 0:
                return f"☀️ 屏幕亮度已增加到 {stdout}%"
        return "❌ 增加亮度失败"

    async def _brightness_down(self) -> str:
        """降低亮度"""
        if self.system == "Windows":
            ps_script = '''
            $current = (Get-CimInstance -Namespace root/wmi -ClassName WmiMonitorBrightness).CurrentBrightness
            $new = [Math]::Max($current - 10, 0)
            $monitor = Get-CimInstance -Namespace root/wmi -ClassName WmiMonitorBrightnessMethods
            $monitor | Invoke-CimMethod -MethodName WmiSetBrightness -Arguments @{Brightness=$new; Timeout=0}
            $new
            '''
            return_code, stdout, stderr = await self._run_powershell(ps_script)
            if return_code == 0:
                return f"☀️ 屏幕亮度已降低到 {stdout}%"
        return "❌ 降低亮度失败"

    # ==================== 显示器控制 ====================
    async def _monitor_off(self) -> str:
        """关闭显示器"""
        if self.system == "Windows":
            try:
                WM_SYSCOMMAND = 0x0112
                SC_MONITORPOWER = 0xF170
                HWND_BROADCAST = 0xFFFF
            
                ctypes.windll.user32.SendMessageW(HWND_BROADCAST, WM_SYSCOMMAND, SC_MONITORPOWER, 2)
                return "🖥️ 显示器已关闭"
            except Exception as e:
                logger.error(f"关闭显示器失败: {e}")
        return "❌ 关闭显示器失败"

    async def _switch_display_output(self, output: str) -> str:
        """切换显示输出"""
        if self.system == "Windows":
            modes = {
                "internal": "internal",
                "external": "external",
                "extend": "extend",
                "duplicate": "clone",
                "clone": "clone"
            }
            mode = modes.get(output.lower(), "internal")
            
            ps_script = f'''
            $ displayswitch = Join-Path $env:SystemRoot "System32\\displayswitch.exe"
            & $displayswitch /{mode}
            '''
            return_code, stdout, stderr = await self._run_powershell(ps_script)
            if return_code == 0:
                return f"🖥️ 显示模式已切换: {output}"
        return "❌ 切换显示输出失败"

    async def _switch_audio_output(self, device: str = None) -> str:
        """切换音频输出设备，不带参数时循环切换到下一个设备"""
        if self.system == "Windows":
            devices = await self._get_audio_devices("Playback")
            if not devices:
                return "❌ 未找到音频输出设备"
            
            if not device:
                current_default = None
                current_index = -1
                for i, d in enumerate(devices):
                    if d.get("Default"):
                        current_default = d
                        current_index = i
                        break
                
                if current_default is None or len(devices) == 1:
                    target_device = devices[0].get('Name', devices[0].get('name', '未知'))
                else:
                    next_index = (current_index + 1) % len(devices)
                    target_device = devices[next_index].get('Name', devices[next_index].get('name', '未知'))
                
                device = target_device
            
            ps_script = f"Import-Module AudioDeviceCmdlets -ErrorAction SilentlyContinue; $device = Get-AudioDevice -List | Where-Object {{ $_.Type -eq 'Playback' -and $_.Name -like '*{device}*' }} | Select-Object -First 1; if ($device) {{ $device | Set-AudioDevice; Write-Output $device.Name }}"
            return_code, stdout, stderr = await self._run_powershell(ps_script)
            if return_code == 0 and stdout.strip():
                return f"🎧 音频输出已切换到: {stdout.strip()}"
        return f"❌ 切换音频输出失败: {device}"

    async def _switch_audio_input(self, device: str = None) -> str:
        """切换音频输入设备（麦克风），不带参数时循环切换到下一个设备"""
        if self.system == "Windows":
            devices = await self._get_audio_devices("Recording")
            if not devices:
                return "❌ 未找到音频输入设备"
            
            if not device:
                current_default = None
                current_index = -1
                for i, d in enumerate(devices):
                    if d.get("Default"):
                        current_default = d
                        current_index = i
                        break
                
                if current_default is None or len(devices) == 1:
                    target_device = devices[0].get('Name', devices[0].get('name', '未知'))
                else:
                    next_index = (current_index + 1) % len(devices)
                    target_device = devices[next_index].get('Name', devices[next_index].get('name', '未知'))
                
                device = target_device
            
            ps_script = f"Import-Module AudioDeviceCmdlets -ErrorAction SilentlyContinue; $device = Get-AudioDevice -List | Where-Object {{ $_.Type -eq 'Recording' -and $_.Name -like '*{device}*' }} | Select-Object -First 1; if ($device) {{ $device | Set-AudioDevice; Write-Output $device.Name }}"
            return_code, stdout, stderr = await self._run_powershell(ps_script)
            if return_code == 0 and stdout.strip():
                return f"🎤 音频输入已切换到: {stdout.strip()}"
        return f"❌ 切换音频输入失败: {device}"

    async def _set_default_audio_output(self, device: str) -> str:
        """设置默认音频输出设备"""
        return await self._switch_audio_output(device)

    async def _set_default_audio_input(self, device: str) -> str:
        """设置默认音频输入设备"""
        return await self._switch_audio_input(device)

    async def _get_audio_devices(self, device_type: str = None) -> list:
        """获取音频设备列表"""
        if self.system == "Windows":
            if device_type:
                ps_script = f"Import-Module AudioDeviceCmdlets -ErrorAction SilentlyContinue; Get-AudioDevice -List | Where-Object {{ $_.Type -eq '{device_type}' }} | Select-Object Name, Default | ConvertTo-Json"
            else:
                ps_script = "Import-Module AudioDeviceCmdlets -ErrorAction SilentlyContinue; Get-AudioDevice -List | Select-Object Type, Name, Default | ConvertTo-Json"
            return_code, stdout, stderr = await self._run_powershell(ps_script)
            logger.info(f"🔍 音频设备查询: return_code={return_code}, stdout={stdout[:200] if stdout else 'empty'}, stderr={stderr}")
            if return_code == 0 and stdout.strip():
                try:
                    import json
                    devices = json.loads(stdout)
                    if isinstance(devices, dict):
                        devices = [devices]
                    logger.info(f"🔍 解析到的设备: {devices}")
                    return devices
                except Exception as e:
                    logger.error(f"🔍 JSON 解析失败: {e}")
        return []

    async def _list_audio_devices(self) -> str:
        """列出音频设备"""
        if self.system == "Windows":
            playback_devices = await self._get_audio_devices("Playback")
            recording_devices = await self._get_audio_devices("Recording")
            
            result = "🎧 音频设备列表:\n\n"
            
            if playback_devices:
                result += "📢 输出设备（扬声器）:\n"
                for i, d in enumerate(playback_devices, 1):
                    default_mark = " [默认]" if d.get("Default") else ""
                    result += f"  {i}. {d.get('Name', d.get('name', '未知'))}{default_mark}\n"
            else:
                result += "📢 输出设备: 未找到\n"
            
            result += "\n"
            
            if recording_devices:
                result += "🎤 输入设备（麦克风）:\n"
                for i, d in enumerate(recording_devices, 1):
                    default_mark = " [默认]" if d.get("Default") else ""
                    result += f"  {i}. {d.get('Name', d.get('name', '未知'))}{default_mark}\n"
            else:
                result += "🎤 输入设备: 未找到\n"
            
            result += "\n💡 使用方法:\n"
            result += "  • 切换扬声器: 切换音频输出 设备名称\n"
            result += "  • 切换麦克风: 切换音频输入 设备名称\n"
            
            return result
        return "❌ 无法获取音频设备列表"

    # ==================== 时间日期 ====================
    def _time_now(self) -> str:
        """当前时间"""
        now = datetime.now()
        return f"🕐 当前时间: {now.strftime('%H:%M:%S')}"

    def _date_today(self) -> str:
        """今天日期"""
        now = datetime.now()
        weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        weekday = weekdays[now.weekday()]
        return f"📅 今天是: {now.strftime('%Y年%m月%d日')} {weekday}"

    # ==================== 清理维护 ====================
    async def _clean_temp(self) -> str:
        """清理临时文件"""
        logger.info(f"🧹 开始清理临时文件")
        if self.system == "Windows":
            temp_paths = [
                os.environ.get('TEMP', ''),
                os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'Temp'),
            ]
            
            logger.info(f"🧹 临时文件路径: {temp_paths}")
            
            cleaned_files = 0
            cleaned_dirs = 0
            errors = 0
            
            for temp_path in temp_paths:
                logger.info(f"🧹 检查路径: {temp_path}, 存在: {os.path.exists(temp_path) if temp_path else False}")
                if not temp_path or not os.path.exists(temp_path):
                    continue
                    
                try:
                    # 递归删除所有文件和子目录
                    for root, dirs, files in os.walk(temp_path, topdown=False):
                        # 删除所有文件
                        for file in files:
                            try:
                                file_path = os.path.join(root, file)
                                os.remove(file_path)
                                cleaned_files += 1
                            except Exception as e:
                                errors += 1
                        
                        # 删除所有空子目录
                        for dir_name in dirs:
                            try:
                                dir_path = os.path.join(root, dir_name)
                                os.rmdir(dir_path)
                                cleaned_dirs += 1
                            except:
                                pass
                except Exception as e:
                    logger.error(f"🧹 清理失败: {e}")
                    errors += 1
            
            logger.info(f"🧹 清理完成: 删除 {cleaned_files} 个文件，{cleaned_dirs} 个目录，跳过 {errors} 个正在使用的文件")
            return f"🧹 清理完成: 删除 {cleaned_files} 个文件，{cleaned_dirs} 个目录，跳过 {errors} 个正在使用的文件"
        logger.error(f"❌ 不支持的操作系统: {self.system}")
        return "❌ 清理失败"

    async def _empty_recycle(self, confirm: bool = False) -> str:
        """清空回收站（需要确认）"""
        if self.system == "Windows":
            if not confirm:
                return "CONFIRM_EMPTY_RECYCLE"
            
            ps_script = 'Clear-RecycleBin -Force -ErrorAction Stop; if ($?) { Write-Output "Recycle bin cleared successfully" } else { Write-Output "Error: Failed to clear recycle bin" }'
            return_code, stdout, stderr = await self._run_powershell(ps_script)
            logger.info(f"🗑️ 清空回收站 - 返回码: {return_code}, stdout: '{stdout}', stderr: '{stderr}'")
            if return_code == 0 and "successfully" in stdout:
                return "🗑️ 回收站已清空"
            elif return_code == 0 and "Error:" in stdout:
                return f"❌ 清空回收站失败: {stdout.replace('Error: ', '').strip()}"
        return "❌ 清空回收站失败"

    # ==================== 通知 ====================
    async def _send_notification(self, title: str, message: str) -> str:
        """发送系统通知"""
        if self.system == "Windows":
            ps_script = f'''
            Add-Type -AssemblyName System.Windows.Forms
            $notification = New-Object System.Windows.Forms.NotifyIcon
            $notification.Icon = [System.Drawing.SystemIcons]::Information
            $notification.BalloonTipIcon = [System.Windows.Forms.ToolTipIcon]::Info
            $notification.BalloonTipTitle = "{title}"
            $notification.BalloonTipText = "{message}"
            $notification.Visible = $true
            $notification.ShowBalloonTip(5000)
            '''
            return_code, stdout, stderr = await self._run_powershell(ps_script)
            if return_code == 0:
                return f"🔔 通知已发送: {title} - {message}"
        return "❌ 发送通知失败"

    def get_capabilities(self) -> list:
        """获取能力列表"""
        return [
            "volume_control",
            "system_power",
            "wifi_control",
            "display_control",
            "audio_device_control",
            "process_management",
            "window_management",
            "clipboard_operations",
            "system_information",
            "application_control",
            "network_operations",
            "service_management",
            "system_settings",
            "cleanup_maintenance",
            "notifications"
        ]
