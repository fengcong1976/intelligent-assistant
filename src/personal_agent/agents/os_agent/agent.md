---
name: system_control
description: 系统控制，包括音量、电源、网络等系统操作
version: "1.0.0"
tags: ["system", "control", "os"]
---

## Description

这个技能用于控制系统设置。支持调节音量、控制电源、管理WiFi、调节亮度等操作。

## When to use

- 用户说"调大音量"
- 用户说"关机"
- 用户说"连接WiFi"
- 用户提到"音量"、"关机"、"重启"、"WiFi"等关键词

## How to use

1. 音量控制：
   - action=volume_set, value=音量值(0-100)
   - action=volume_mute 静音
   - action=volume_unmute 取消静音
   
2. 电源控制：
   - action=sleep 睡眠
   - action=shutdown 关机
   - action=restart 重启
   
3. WiFi管理：
   - action=wifi_list 列出WiFi
   - action=wifi_connect, name=WiFi名, password=密码
   - action=wifi_status 状态

## Edge cases

- 权限不足时，提示用户
- 操作不可逆时，确认用户意图
- 设备不支持时，告知用户
