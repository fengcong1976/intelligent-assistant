---
name: search_web
description: 搜索网络信息，获取新闻、资讯、旅游攻略等
version: "1.0.0"
tags: ["search", "web", "information", "news"]
---

## Description

这个技能用于搜索网络信息。可以搜索新闻、资讯、旅游攻略、技术文档等。支持关键词搜索和自然语言搜索。

## When to use

- 用户说"搜索XXX"
- 用户说"查一下XXX"
- 用户说"最近有什么新闻"
- 用户说"XXX旅游攻略"
- 用户需要获取网络上的信息

## How to use

1. 提取搜索关键词：
   - 从用户请求中提取搜索关键词
   - 如果是自然语言，提取核心实体
   
2. 选择搜索方式：
   - 新闻资讯：调用 news_agent 或 crawler_agent
   - 旅游攻略：调用 crawler_agent 搜索
   - 通用搜索：调用 crawler_agent
   
3. 处理搜索结果：
   - 总结搜索结果
   - 提取关键信息
   - 以友好的方式呈现给用户

## Edge cases

- 搜索无结果时，建议用户换关键词
- 搜索结果过多时，只展示最相关的几条
- 网络错误时，告知用户稍后重试
- 用户问敏感话题时，委婉拒绝
