---
name: calendar
description: 日历管理智能体，支持创建、查询、修改、删除日程事件
version: "1.0.0"
tags: ["calendar", "schedule", "reminder", "event", "日程", "日历"]
---

## Description

日历管理智能体，帮助用户管理个人日程安排。支持创建日程事件、查询日程、设置提醒、修改和删除日程等功能。所有数据存储在本地，保护用户隐私。

## When to use

- 用户说"添加日程"、"创建日程"、"新建日程"
- 用户说"明天有什么安排"、"今天日程"、"本周计划"
- 用户说"提醒我开会"、"设置提醒"
- 用户说"删除日程"、"取消日程"
- 用户说"修改日程"、"更改时间"
- 用户提到"日程"、"日历"、"安排"、"计划"、"提醒"等关键词
- 用户需要查看或管理时间安排

## How to use

### add_event
添加日程事件
- title: 事件标题（必需）
- date: 日期，格式如 "2024-01-15" 或 "明天"、"下周一"（必需）
- time: 时间，格式如 "14:00" 或 "下午2点"（可选）
- duration: 持续时间，如 "1小时"、"30分钟"（可选）
- location: 地点（可选）
- description: 详细描述（可选）
- reminder: 提醒时间，如 "提前15分钟"、"提前1小时"（可选）
- repeat: 重复规则，如 "每天"、"每周"、"每月"（可选）

示例:
- "添加明天下午3点的会议" -> action=add_event, title=会议, date=明天, time=15:00
- "下周一上午10点有个面试，地点在科技园" -> action=add_event, title=面试, date=下周一, time=10:00, location=科技园
- "每天早上8点提醒我吃药" -> action=add_event, title=吃药, time=08:00, repeat=每天

### query_events
查询日程
- date: 查询日期（可选，默认今天）
- start_date: 开始日期（可选）
- end_date: 结束日期（可选）
- keyword: 关键词搜索（可选）

示例:
- "今天有什么安排" -> action=query_events, date=今天
- "明天日程" -> action=query_events, date=明天
- "本周计划" -> action=query_events, start_date=本周一, end_date=本周日
- "下周有什么会议" -> action=query_events, start_date=下周一, end_date=下周日, keyword=会议

### update_event
修改日程
- event_id: 事件ID（可选，用于精确匹配）
- title: 原事件标题（用于模糊匹配）
- new_title: 新标题（可选）
- new_date: 新日期（可选）
- new_time: 新时间（可选）
- new_location: 新地点（可选）
- new_description: 新描述（可选）

示例:
- "把明天的会议改到后天" -> action=update_event, title=会议, new_date=后天
- "修改下午的面试时间到3点" -> action=update_event, title=面试, new_time=15:00

### delete_event
删除日程
- event_id: 事件ID（可选，用于精确匹配）
- title: 事件标题（用于模糊匹配）
- date: 日期（可选，用于缩小范围）

示例:
- "删除明天的会议" -> action=delete_event, title=会议, date=明天
- "取消下午的安排" -> action=delete_event, title=安排, date=今天

### list_upcoming
查看即将到来的日程
- count: 数量（可选，默认5个）
- days: 未来几天（可选）

示例:
- "最近有什么安排" -> action=list_upcoming, count=5
- "未来三天有什么事" -> action=list_upcoming, days=3

## Edge cases

- 时间冲突时提示用户已有日程，询问是否继续添加
- 找不到事件时列出相似事件供用户选择
- 日期格式不明确时询问用户确认
- 删除日程前确认用户意图
- 重复日程修改时询问是修改单个还是全部
- 时间已过的日程添加时提醒用户
- 跨天日程需要特殊处理显示
