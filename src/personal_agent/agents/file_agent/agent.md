---
name: file_management
description: 文件和文件夹管理，包括查看、搜索、整理文件
version: "1.0.0"
tags: ["file", "folder", "management"]
---

## Description

这个技能用于管理电脑上的文件和文件夹。支持查看磁盘空间、搜索文件、统计文件数量、查找大文件等操作。

## When to use

- 用户说"查看磁盘空间"
- 用户说"搜索XXX文件"
- 用户说"哪个文件夹最大"
- 用户说"有多少个文件"
- 用户提到"文件"、"文件夹"、"磁盘"等关键词

## How to use

1. 磁盘空间查询：
   - action=disk_space
   - 返回各磁盘的使用情况
   
2. 文件搜索：
   - action=search_files
   - params: pattern=搜索模式, path=搜索路径
   
3. 文件统计：
   - action=count_files
   - params: path=目录路径
   
4. 大文件查找：
   - action=largest_folder
   - params: path=目录路径, count=数量

## Edge cases

- 路径不存在时，提示用户
- 权限不足时，告知用户
- 搜索时间过长时，提供进度反馈
