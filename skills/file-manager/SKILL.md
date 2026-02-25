---
name: file-manager
description: 文件管理工具，支持文件搜索、复制、移动、删除、重命名等操作
version: 1.0.0
author: Personal Agent
permissions: 文件系统读写
---

# File Manager Skill

## 1. Description
文件管理工具，提供完整的文件和文件夹操作能力，包括：
- 列出目录内容
- 创建文件夹
- 复制文件/文件夹
- 移动文件/文件夹
- 重命名文件/文件夹
- 删除文件/文件夹
- 搜索文件
- 获取文件信息

## 2. When to use
- 用户需要查看某个目录的内容
- 用户需要创建、重命名或删除文件夹
- 用户需要复制或移动文件
- 用户需要搜索特定文件
- 用户需要整理文件结构
- 用户说"把xxx文件夹改名为xxx"
- 用户说"把xxx文件移动到xxx"
- 用户说"删除xxx文件"

## 3. How to use

### 3.1 列出目录内容
```powershell
# PowerShell
Get-ChildItem -Path "目录路径"
Get-ChildItem -Path "E:\项目" -Recurse  # 递归列出
```

### 3.2 创建文件夹
```powershell
New-Item -ItemType Directory -Path "文件夹路径"
New-Item -ItemType Directory -Path "E:\新文件夹" -Force
```

### 3.3 重命名文件/文件夹
```powershell
Rename-Item -Path "原路径" -NewName "新名称"
Rename-Item -Path "E:\智能助手" -NewName "SmartAssistant"
```

### 3.4 移动文件/文件夹
```powershell
Move-Item -Path "源路径" -Destination "目标路径"
Move-Item -Path "E:\test.txt" -Destination "E:\backup\"
```

### 3.5 复制文件/文件夹
```powershell
Copy-Item -Path "源路径" -Destination "目标路径" -Recurse
Copy-Item -Path "E:\folder" -Destination "E:\backup\" -Recurse
```

### 3.6 删除文件/文件夹
```powershell
Remove-Item -Path "路径" -Recurse -Force
Remove-Item -Path "E:\test.txt"
Remove-Item -Path "E:\folder" -Recurse  # 删除文件夹及其内容
```

### 3.7 搜索文件
```powershell
Get-ChildItem -Path "搜索路径" -Filter "*.txt" -Recurse
Get-ChildItem -Path "E:\" -Filter "*.pdf" -Recurse -ErrorAction SilentlyContinue
```

### 3.8 获取文件信息
```powershell
Get-Item -Path "文件路径" | Select-Object Name, Length, LastWriteTime
```

## 4. Edge cases
- 文件/文件夹不存在时，返回友好的错误信息
- 目标已存在时，询问用户是否覆盖
- 权限不足时，提示用户以管理员身份运行
- 路径包含空格时，使用引号包裹路径
- 中文路径完全支持，无需特殊处理

## 5. Examples

### 示例1：重命名文件夹
用户：把e盘智能助手文件夹改名为英文名
执行：Rename-Item -Path "E:\智能助手" -NewName "SmartAssistant"

### 示例2：创建文件夹
用户：在D盘创建一个叫"工作资料"的文件夹
执行：New-Item -ItemType Directory -Path "D:\工作资料" -Force

### 示例3：移动文件
用户：把桌面的test.txt移动到D盘
执行：Move-Item -Path "$env:USERPROFILE\Desktop\test.txt" -Destination "D:\"

### 示例4：搜索文件
用户：在E盘找所有的PDF文件
执行：Get-ChildItem -Path "E:\" -Filter "*.pdf" -Recurse -ErrorAction SilentlyContinue

### 示例5：删除文件夹
用户：删除E盘的temp文件夹
执行：Remove-Item -Path "E:\temp" -Recurse -Force
