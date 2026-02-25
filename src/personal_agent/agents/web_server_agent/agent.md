---
name: web_server
description: Web服务管理，启动和管理Web界面服务
version: "1.0.0"
tags: ["web", "server", "remote"]
---

## Description

这个技能用于管理Web服务。支持启动Web服务、停止服务、查看服务状态、显示访问二维码等操作。

## When to use

- 用户说"启动Web服务"
- 用户说"显示二维码"
- 用户说"Web服务状态"
- 用户提到"Web服务"、"远程访问"等关键词

## How to use

1. 启动服务：
   - action=start_web_server
   - 返回访问地址和二维码
   
2. 停止服务：
   - action=stop_web_server
   
3. 查看状态：
   - action=get_web_status
   
4. 显示二维码：
   - action=show_qr_code

## Edge cases

- 端口被占用时，尝试其他端口
- 服务启动失败时，检查网络配置
- 二维码显示失败时，提供文字地址
