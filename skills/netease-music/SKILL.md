---
name: netease-music
description: 智能控制网页版网易云音乐，支持播放、暂停、搜索歌曲、切换歌曲等功能
version: 1.0.0
author: Personal Agent
permissions: 浏览器自动化控制权限
---

# Netease Music Control Skill

## 1. Description
通过浏览器自动化技术控制网页版网易云音乐，实现智能音乐播放控制。

**支持的功能：**
- 🎵 播放/暂停音乐
- 🔍 搜索并播放指定歌曲
- ⏭️ 下一首/上一首
- 🔊 音量控制
- 📝 显示当前播放信息

**技术实现：**
- 使用 Playwright 控制浏览器
- 自动打开 music.163.com
- 模拟用户操作控制播放器

## 2. When to use
- 用户说："播放音乐"
- 用户说："播放歌曲 [歌名]"
- 用户说："播放 [歌手] 的 [歌名]"
- 用户说："播放网易云音乐"
- 用户说："暂停音乐"
- 用户说："下一首"
- 用户说："上一首"
- 用户说："音量调大/调小"
- 用户说："播放 头发乱了"

## 3. How to use
根据用户指令执行相应操作：

**播放指定歌曲：**
```python
execute(action="play", song_name="歌曲名", artist="歌手名(可选)")
```

**播放/暂停：**
```python
execute(action="toggle")
```

**下一首：**
```python
execute(action="next")
```

**上一首：**
```python
execute(action="previous")
```

**音量控制：**
```python
execute(action="volume_up")    # 音量+
execute(action="volume_down")  # 音量-
```

**获取播放信息：**
```python
execute(action="info")
```

## 4. Edge cases
- 网页未打开：自动打开网易云音乐网页
- 歌曲未找到：提示用户确认歌曲名称
- 需要登录：提示用户先登录网易云音乐账号
- 浏览器未安装：提示用户安装 Chrome 或 Edge

## 5. Performance
- 启动时间：3-5秒（首次打开浏览器）
- 操作响应：<1秒
- 支持后台运行
