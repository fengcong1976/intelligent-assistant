---
name: file_download
description: 文件下载管理，支持单文件和批量下载
version: "1.0.0"
tags: ["download", "file", "internet"]
---

## Description

这个技能用于下载文件。支持单个文件下载、批量下载、断点续传等功能。

## When to use

- 用户说"下载XXX"
- 用户说"保存这个文件"
- 用户提到"下载"、"保存"等关键词
- 需要从网络获取文件时

## How to use

1. 单文件下载：
   - action=download
   - params: url=下载地址, save_path=保存路径
   
2. 批量下载：
   - action=batch_download
   - params: urls=地址列表, save_dir=保存目录

## Edge cases

- 下载失败时，提示错误原因
- 文件已存在时，询问是否覆盖
- 下载时间过长时，显示进度
