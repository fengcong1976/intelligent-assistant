---
name: app_management
description: 应用程序管理，包括打开、关闭、查看应用程序
version: "1.0.0"
tags: ["app", "application", "software"]
---

## Description

这个技能用于管理电脑上的应用程序。支持打开应用程序、关闭应用程序、查看运行中的应用、列出已安装应用等操作。

## When to use

- 用户说"打开XXX"
- 用户说"关闭XXX"
- 用户说"正在运行什么程序"
- 用户提到"应用"、"程序"、"软件"等关键词

## How to use

1. 打开应用：
   - action=open
   - params: app_name=应用名
   
2. 关闭应用：
   - action=close
   - params: app_name=应用名
   
3. 查看运行中：
   - action=list_running
   
4. 列出已安装：
   - action=list_installed

## Edge cases

- 应用不存在时，提示用户或搜索
- 应用已在运行时，切换到前台
- 关闭失败时，提示用户手动关闭
