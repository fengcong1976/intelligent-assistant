---
name: system-info
description: 系统信息查询工具，获取CPU、内存、磁盘、网络等系统状态
version: 1.0.0
author: Personal Agent
permissions: 系统信息读取权限
---

# System Info Skill

## 1. Description
帮助用户查询系统状态信息，包括CPU使用率、内存使用情况、磁盘空间、网络状态、运行时间等。

## 2. When to use
- 用户说："查看系统状态"
- 用户说："CPU使用率多少"
- 用户说："内存还剩多少"
- 用户说："磁盘空间够不够"
- 用户说："电脑运行多久了"
- 用户说："查看网络连接状态"

## 3. How to use
1. 识别用户要查询的信息类型
2. 执行相应的系统命令获取信息：
   - CPU：wmic cpu get loadpercentage
   - 内存：wmic OS get TotalVisibleMemorySize,FreePhysicalMemory
   - 磁盘：wmic logicaldisk get size,freespace,caption
   - 运行时间：wmic os get lastbootuptime
3. 格式化输出结果

## 4. Edge cases
- 命令执行失败：返回错误信息
- 权限不足：提示需要管理员权限
