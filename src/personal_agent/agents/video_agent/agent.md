---
name: play_video
description: 播放视频，支持本地视频和在线视频
version: "1.0.0"
tags: ["video", "play", "entertainment"]
---

## Description

这个技能用于播放视频。支持播放本地视频文件，也支持播放在线视频链接。可以搜索视频、控制播放进度。

## When to use

- 用户说"播放XXX视频"
- 用户说"看个电影"
- 用户说"打开视频"
- 用户提到"视频"、"电影"、"播放"等关键词
- 用户想暂停、继续、切换视频

## How to use

1. 解析用户请求：
   - 提取视频名称、文件路径或URL
   - 判断是本地视频还是在线视频
   
2. 播放控制：
   - 播放：action=play
   - 暂停：action=pause
   - 继续：action=resume
   - 停止：action=stop
   - 下一个：action=next
   - 上一个：action=previous

## Edge cases

- 找不到视频时，告知用户
- 视频格式不支持时，提示支持的格式
- 在线视频加载失败时，检查网络连接
