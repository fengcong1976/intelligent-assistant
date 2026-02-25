---
name: generate-qr-code
description: 生成二维码，支持文本、URL等内容，可自定义尺寸和颜色
version: 1.0.0
author: Personal Agent
permissions: 文件写入权限（用于保存二维码图片）
---

# Generate QR Code Skill

## 1. Description
当用户需要将文本、URL等转换为可视化二维码时，使用此技能生成二维码图片，并保存到指定路径。

## 2. When to use
- 用户说："帮我把 https://example.com 生成二维码"
- 用户说："生成一个包含'Hello World'的二维码"
- 用户说："帮我做一个二维码，内容是我的手机号"

## 3. How to use
1. 从用户消息中提取生成内容
2. 可选：提取尺寸（默认300px）、颜色（默认黑色）
3. 调用 agent.py 中的 generate_qr 函数执行生成
4. 返回保存路径

## 4. Implementation
- 依赖库：qrcode, Pillow
- 核心函数：async def generate_qr(text: str, size: int = 300, color: str = "black", save_path: str = None)
- 参数说明：
  - text：二维码内容（必选）
  - size：二维码尺寸（默认300px）
  - color：填充颜色（默认黑色）
  - save_path：保存路径（默认桌面）

## 5. Edge cases
- 内容为空：提示用户提供内容
- 保存路径无权限：更换保存路径
- 未安装依赖库：自动尝试安装
