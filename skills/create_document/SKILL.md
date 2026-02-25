---
name: create_document
description: 创建和编辑文档，支持 Word、PDF、Markdown 等格式
version: "1.0.0"
tags: ["document", "create", "edit", "pdf", "word"]
---

## Description

这个技能用于创建和编辑各种文档。支持创建 Word 文档、PDF 文档、Markdown 文件等。可以根据用户描述生成文档内容。

## When to use

- 用户说"帮我写一份文档"
- 用户说"生成一个PDF"
- 用户说"创建Word文档"
- 用户提到"文档"、"报告"、"方案"等关键词
- 用户需要整理内容成文档

## How to use

1. 确定文档类型：
   - 根据用户请求判断文档格式（Word、PDF、Markdown）
   - 如果用户没有指定，默认使用 Word 格式
   
2. 生成文档内容：
   - 使用 LLM 根据用户描述生成文档内容
   - 支持生成大纲、正文、表格等
   
3. 创建文档：
   - Word：调用 pdf_agent 或 file_agent 创建 .docx 文件
   - PDF：调用 pdf_agent 创建 .pdf 文件
   - Markdown：直接写入 .md 文件
   
4. 保存和发送：
   - 保存到用户指定位置或默认目录
   - 可以选择发送到邮箱

## Edge cases

- 用户描述不清晰时，询问文档主题和格式
- 文档内容较长时，分段生成避免超时
- 保存路径不存在时，使用默认路径
- 用户要求编辑已有文档时，先读取再修改
