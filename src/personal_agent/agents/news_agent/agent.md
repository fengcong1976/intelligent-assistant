---
name: fetch_news
description: 获取新闻资讯，支持多个新闻源
version: "1.0.0"
tags: ["news", "information", "rss"]
---

## Description

这个技能用于获取新闻资讯。支持从多个新闻源获取最新新闻，包括科技、财经、综合等类型。

## When to use

- 用户说"今天有什么新闻"
- 用户说"获取最新资讯"
- 用户说"科技新闻"
- 用户提到"新闻"、"资讯"、"热点"等关键词

## How to use

1. 获取新闻：
   - action=fetch_news
   - params: count=数量, category=分类, source=来源
   
2. 获取热点：
   - action=fetch_hot
   - params: count=数量
   
3. 搜索新闻：
   - action=search_news
   - params: keyword=关键词

## Edge cases

- 新闻源不可用时，尝试其他来源
- 网络超时时，提示用户稍后重试
- 无新闻时，返回默认提示
