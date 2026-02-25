---
name: ncm_to_mp3
description: NCM音频解密智能体 - 解密网易云音乐.ncm文件并转为MP3格式
version: "1.0.0"
tags: ["audio", "decrypt", "ncm", "converter"]
---

## Description

NCM音频解密智能体 - 专用于解密网易云音乐.ncm加密音频文件，转换为标准MP3格式。

支持解密：
- 网易云音乐 .ncm 格式
- QQ音乐 .qmc 格式（待实现）
- 酷我音乐 .kwm 格式（待实现）

## When to use

- 用户说"把这个ncm文件转成mp3"
- 用户说"解密这个ncm文件"
- 用户说"转换ncm格式"
- 用户拖入.ncm文件并要求转换

## How to use

### decrypt_ncm
解密单个NCM文件为MP3格式
- file_path: NCM文件路径
- output_dir: 输出目录（可选，默认原目录）

示例:
- "把这个ncm文件转成mp3" -> action=decrypt_ncm, file_path=xxx.ncm
- "解密这个文件" -> action=decrypt_ncm, file_path=xxx.ncm

### batch_decrypt
批量解密多个NCM文件
- files: NCM文件路径列表
- output_dir: 输出目录（可选）

示例:
- "批量解密这些ncm文件" -> action=batch_decrypt, files=[file1.ncm, file2.ncm]

## Edge cases

- 文件不是有效的NCM格式：返回错误提示
- 文件已损坏：返回错误提示
- 输出目录不存在：自动创建
- 目标文件已存在：覆盖

## Implementation Notes

1. 使用AES-ECB解密核心密钥
2. 使用密钥盒算法解密音频数据
3. 输出标准MP3格式
4. 保留原始文件名（仅改扩展名）

## Dependencies

- pycryptodome: AES解密
