---
name: code_development
description: 代码开发和项目管理，支持代码生成、修改、审查
version: "1.0.0"
tags: ["code", "development", "programming"]
---

## Description

这个技能用于辅助代码开发。支持代码生成、代码修改、代码审查、创建新模块等操作。

## When to use

- 用户说"帮我写一段代码"
- 用户说"创建一个新模块"
- 用户说"审查这段代码"
- 用户提到"代码"、"编程"、"开发"等关键词
- 需要修改或创建智能体时

## How to use

1. 代码生成：
   - action=generate_code
   - params: description=功能描述, language=编程语言
   
2. 代码修改：
   - action=modify_agent
   - params: agent_name=智能体名, changes=修改内容
   
3. 创建模块：
   - action=create_module
   - params: name=模块名, type=类型
   
4. 代码审查：
   - action=review_code
   - params: file_path=文件路径

## Edge cases

- 代码执行有风险时，提示用户确认
- 文件不存在时，询问是否创建
- 依赖缺失时，提示安装
