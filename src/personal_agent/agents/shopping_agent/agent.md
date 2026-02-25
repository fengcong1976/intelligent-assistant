---
name: shopping
version: "1.0.0"
description: 购物助手智能体，支持商品比价、优惠信息聚合、购物清单管理、个性化商品推荐等功能
tags: ["shopping", "price comparison", "deals", "shopping list", "recommendation", "购物", "比价", "优惠", "清单", "推荐"]
---

## Description

购物助手智能体，帮助用户管理购物相关的各种需求。支持商品搜索、比价、优惠信息获取、购物清单管理等功能。所有数据存储在本地，保护用户隐私。

## When to use

- 用户说"搜索商品"、"查找商品"、"搜索iPhone"
- 用户说"比价商品"、"对比价格"、"比价AirPods"
- 用户说"查看优惠"、"优惠信息"、"特价活动"
- 用户说"创建购物清单"、"新建清单"、"添加清单"
- 用户说"查看购物清单"、"我的清单"、"购物清单"
- 用户说"添加商品"、"删除商品"、"修改商品"
- 用户说"推荐商品"、"给我推荐"、"有什么推荐"
- 用户提到"购物"、"价格"、"优惠"、"清单"、"推荐"等关键词
- 用户需要购物相关的帮助和信息

## How to use

### search_products
搜索商品
- keyword: 商品关键词（必需）
- category: 商品分类（可选）

示例:
- "搜索iPhone" -> action=search_products, keyword=iPhone
- "查找运动鞋" -> action=search_products, keyword=运动鞋, category=服装鞋包

### compare_prices
商品比价
- product_name: 商品名称（必需）

示例:
- "比价AirPods" -> action=compare_prices, product_name=AirPods
- "对比iPhone价格" -> action=compare_prices, product_name=iPhone

### query_deals
获取优惠信息
- category: 商品分类（可选）

示例:
- "查看优惠" -> action=query_deals
- "电子产品优惠" -> action=query_deals, category=电子产品

### create_list
创建购物清单
- name: 清单名称（必需）

示例:
- "创建购物清单 日常用品" -> action=create_list, name=日常用品
- "新建清单 生日礼物" -> action=create_list, name=生日礼物

### list_lists
查看购物清单

示例:
- "查看我的购物清单" -> action=list_lists
- "我的清单" -> action=list_lists

### add_item
添加商品到购物清单
- list_id: 清单ID（可选，默认使用第一个清单）
- name: 商品名称（必需）
- price: 商品价格（可选）
- quantity: 商品数量（可选，默认1）
- category: 商品分类（可选）
- store: 购买店铺（可选）
- url: 商品链接（可选）
- notes: 备注信息（可选）

示例:
- "添加商品到购物清单 牛奶" -> action=add_item, name=牛奶
- "添加商品 苹果 5个" -> action=add_item, name=苹果, quantity=5

### delete_item
删除购物清单中的商品
- list_id: 清单ID（必需）
- item_id: 商品ID（必需）

示例:
- "删除商品" -> action=delete_item, list_id=list_123, item_id=item_456

### toggle_item
标记商品状态
- list_id: 清单ID（必需）
- item_id: 商品ID（必需）

示例:
- "标记商品" -> action=toggle_item, list_id=list_123, item_id=item_456

### recommend_products
推荐商品
- category: 商品分类（可选）

示例:
- "推荐商品" -> action=recommend_products
- "推荐电子产品" -> action=recommend_products, category=电子产品
