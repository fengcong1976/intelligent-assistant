---
name: crawler_agent
description: 网络搜索和网页抓取，获取互联网信息
version: "1.0.0"
tags: ["search", "web", "crawler", "information", "download", "news"]
---

## Description

这个技能用于搜索网络信息和抓取网页内容。支持关键词搜索、网页内容提取、链接抓取、文件下载等操作。

## When to use

### 网页搜索
- 用户说"搜索XXX"、"搜一下XXX"、"查一下XXX"
- 用户说"百度一下"、"谷歌搜索"
- 用户说"搜索资料"、"搜索信息"
- 用户提到"搜索"、"查找"、"查询"等关键词

### 新闻搜索
- 用户说"看新闻"、"查新闻"、"最新新闻"
- 用户说"热搜"、"热搜榜"、"热点新闻"

### 网页抓取
- 用户说"打开XXX网站"、"访问XXX网页"
- 用户说"抓取网页"、"获取网页内容"
- 用户说"读取网页"

### 文件下载
- 用户说"下载XXX"、"帮我下载"
- 用户说"下载图片"、"下载视频"、"下载文件"

### 图片/视频搜索
- 用户说"搜索图片"、"搜图片"、"找图片"
- 用户说"搜索视频"、"搜视频"、"找视频"

### 链接提取
- 用户说"提取链接"、"获取链接"
- 用户说"抓取视频链接"

## How to use

1. 网页搜索：
   - action=web_search
   - params: query=搜索关键词
   
2. 网页抓取：
   - action=crawl_webpage
   - params: url=网页地址
   
3. 链接提取：
   - action=scrape_links
   - params: url=网页地址, pattern=链接模式
   
4. 文件下载：
   - action=file_download
   - params: url=下载地址, save_path=保存路径

5. 图片搜索：
   - action=image_search
   - params: query=图片关键词

6. 视频搜索：
   - action=video_search
   - params: query=视频关键词

## Edge cases

- 搜索无结果时，建议换关键词
- 网页无法访问时，检查网络或URL
- 内容过长时，提供摘要
- 下载大文件时，提示等待时间
