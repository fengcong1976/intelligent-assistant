---
name: web_crawler
description: 网络搜索和网页抓取工具，获取互联网信息
version: 1.0.0
---

# 网络爬虫工具

## 功能说明
本工具用于搜索网络信息和抓取网页内容，支持以下功能：
- 网页搜索（关键词搜索）
- 网页内容抓取
- 链接提取
- 文件下载
- 图片搜索
- 视频搜索
- 新闻搜索

## 参数说明

### web_search（网页搜索）
- `query`: 搜索关键词
  - 类型：string
  - 示例："人工智能"、"最新科技"
  - 说明：必需参数

- `engine`: 搜索引擎
  - 类型：string
  - 示例："baidu"、"google"、"bing"
  - 说明：可选参数，默认baidu

- `count`: 结果数量
  - 类型：integer
  - 示例：10
  - 说明：可选参数，默认10条

### crawl_webpage（抓取网页）
- `url`: 网页地址
  - 类型：string
  - 示例："https://www.example.com"
  - 说明：必需参数

- `extract_text`: 是否提取文本
  - 类型：boolean
  - 示例：true
  - 说明：可选参数，默认true

- `extract_links`: 是否提取链接
  - 类型：boolean
  - 示例：false
  - 说明：可选参数，默认false

### scrape_links（提取链接）
- `url`: 网页地址
  - 类型：string
  - 示例："https://www.example.com"
  - 说明：必需参数

- `pattern`: 链接模式
  - 类型：string
  - 示例："*.pdf"
  - 说明：可选参数，默认所有链接

### file_download（文件下载）
- `url`: 下载地址
  - 类型：string
  - 示例："https://example.com/file.pdf"
  - 说明：必需参数

- `save_path`: 保存路径
  - 类型：string
  - 示例："C:/Users/xxx/Downloads/file.pdf"
  - 说明：可选参数，默认Downloads目录

### image_search（图片搜索）
- `query`: 搜索关键词
  - 类型：string
  - 示例："风景"、"猫咪"
  - 说明：必需参数

- `count`: 结果数量
  - 类型：integer
  - 示例：10
  - 说明：可选参数，默认10张

### video_search（视频搜索）
- `query`: 搜索关键词
  - 类型：string
  - 示例："教程"、"新闻"
  - 说明：必需参数

- `count`: 结果数量
  - 类型：integer
  - 示例：10
  - 说明：可选参数，默认10个

### search_news（新闻搜索）
- `query`: 搜索关键词
  - 类型：string
  - 示例："科技"
  - 说明：可选参数

- `count`: 结果数量
  - 类型：integer
  - 示例：10
  - 说明：可选参数，默认10条

## 使用场景

### 场景1：网页搜索
```
用户："搜索人工智能"
调用：web_search(query="人工智能")
```

### 场景2：抓取网页
```
用户："打开https://www.example.com"
调用：crawl_webpage(url="https://www.example.com")
```

### 场景3：提取链接
```
用户："提取https://www.example.com的所有PDF链接"
调用：scrape_links(url="https://www.example.com", pattern="*.pdf")
```

### 场景4：下载文件
```
用户："下载https://example.com/file.pdf"
调用：file_download(url="https://example.com/file.pdf", save_path="C:/Users/xxx/Downloads/file.pdf")
```

### 场景5：搜索图片
```
用户："搜索风景图片"
调用：image_search(query="风景")
```

### 场景6：搜索视频
```
用户："搜索Python教程"
调用：video_search(query="Python教程")
```

## 返回信息

### web_search返回
- 搜索结果标题
- 搜索结果摘要
- 搜索结果链接
- 相关度评分

### crawl_webpage返回
- 网页标题
- 网页内容（文本）
- 提取的链接（如果extract_links=true）
- 网页元数据

### scrape_links返回
- 链接列表
- 链接文本
- 链接类型

### file_download返回
- 下载状态
- 文件保存路径
- 文件大小
- 下载时间

### image_search返回
- 图片链接
- 图片标题
- 图片尺寸
- 图片来源

### video_search返回
- 视频标题
- 视频链接
- 视频时长
- 视频来源

## 注意事项

### 1. 搜索引擎
- 支持的搜索引擎：百度、谷歌、必应
- 默认使用百度
- 不同搜索引擎结果可能不同

### 2. 网页访问
- 需要网络连接
- 某些网站可能无法访问
- 网页加载超时会提示用户

### 3. 内容提取
- 自动去除广告和无关内容
- 保留主要文本内容
- 支持中文和英文

### 4. 文件下载
- 大文件下载可能较慢
- 会显示下载进度
- 下载失败时会提示重试

### 5. 图片和视频搜索
- 搜索结果来自公开资源
- 版权信息需要用户自行确认
- 建议使用正版资源

## 常见问题

### Q1：可以搜索任何内容吗？
A：可以搜索公开的网页内容，但受搜索引擎限制。

### Q2：网页抓取失败怎么办？
A：检查网络连接，确认URL是否正确，或稍后重试。

### Q3：下载的文件保存在哪里？
A：默认保存在Downloads目录，可以指定保存路径。

### Q4：可以抓取需要登录的网页吗？
A：当前版本不支持，需要登录的网页无法抓取。

## 示例对话

### 示例1：网页搜索
```
用户：搜索人工智能
系统：搜索结果：
1. 人工智能的最新发展...
2. AI技术的应用场景...
3. 人工智能的未来趋势...
...
```

### 示例2：抓取网页
```
用户：打开https://www.example.com
系统：已抓取网页：
标题：示例网站
内容：这是网页的主要内容...
```

### 示例3：下载文件
```
用户：下载https://example.com/file.pdf
系统：正在下载...
下载完成：C:/Users/xxx/Downloads/file.pdf (2.5MB)
```

## 相关工具
- `query_tools`: 查询可用工具
- `file_management`: 文件管理（可以管理下载的文件）
- `send_email`: 发送邮件（可以将下载的文件作为附件发送）
