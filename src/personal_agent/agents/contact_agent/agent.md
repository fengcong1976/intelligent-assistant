---
name: contact_management
description: 联系人管理，包括添加、查询、更新联系人信息
version: "1.0.0"
tags: ["contact", "address", "management"]
---

## Description

这个技能用于管理联系人信息。支持添加新联系人、查询联系人、更新联系人信息、删除联系人等操作。

## When to use

- 用户说"添加联系人"
- 用户说"查询XXX的联系方式"
- 用户说"XXX的电话是多少"
- 用户说"列出所有联系人"
- 用户说"有哪些联系人"
- 用户提到"联系人"、"通讯录"、"电话"等关键词
- 发送邮件时需要查找收件人邮箱

## How to use

1. 列出所有联系人：
   - action=list
   - params: relationship=关系类型（可选，如"同学"、"同事"、"家人"）
   - 示例: "列出所有联系人" -> action=list
   - 示例: "同学有哪些" -> action=list, relationship=同学
   - 示例: "我的同事" -> action=list, relationship=同事
   
2. 添加联系人：
   - action=add
   - params: name=姓名, phone=电话, email=邮箱
   
3. 查询联系人：
   - action=query
   - params: name=姓名或关键词
   - 示例: "李四的邮箱" -> action=query, name=李四
   
4. 更新联系人：
   - action=update
   - params: name=姓名, 更新的字段
   
5. 删除联系人：
   - action=delete
   - params: name=姓名

## Edge cases

- 联系人不存在时，提示用户是否添加
- 查询结果多个时，列出所有匹配项
- 联系人信息不完整时，询问用户补充
