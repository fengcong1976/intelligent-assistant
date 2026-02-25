---
name: file_management
description: 文件和文件夹管理工具，包括查看、搜索、整理文件
version: 1.0.0
---

# 文件管理工具

## 功能说明
本工具用于管理电脑上的文件和文件夹，支持以下功能：
- 查看磁盘空间使用情况
- 搜索文件
- 统计文件数量
- 查找大文件
- 查找最大的文件夹
- 列出目录内容

## 参数说明

### disk_space（查看磁盘空间）
- 无参数

### search_files（搜索文件）
- `pattern`: 搜索模式
  - 类型：string
  - 示例："*.pdf"、"report.*"
  - 说明：必需参数，支持通配符

- `path`: 搜索路径
  - 类型：string
  - 示例："C:/Users/xxx/Documents"
  - 说明：可选参数，默认当前目录

- `recursive`: 是否递归搜索
  - 类型：boolean
  - 示例：true
  - 说明：可选参数，默认true

### count_files（统计文件数量）
- `path`: 目录路径
  - 类型：string
  - 示例："C:/Users/xxx/Documents"
  - 说明：必需参数

### largest_folder（查找最大的文件夹）
- `path`: 目录路径
  - 类型：string
  - 示例："C:/Users/xxx"
  - 说明：必需参数

- `count`: 返回数量
  - 类型：integer
  - 示例：5
  - 说明：可选参数，默认5个

### list_directory（列出目录内容）
- `path`: 目录路径
  - 类型：string
  - 示例："C:/Users/xxx/Documents"
  - 说明：必需参数

- `show_hidden`: 是否显示隐藏文件
  - 类型：boolean
  - 示例：false
  - 说明：可选参数，默认false

## 使用场景

### 场景1：查看磁盘空间
```
用户："查看磁盘空间"
调用：disk_space()
```

### 场景2：搜索文件
```
用户："搜索所有PDF文件"
调用：search_files(pattern="*.pdf")
```

### 场景3：在指定目录搜索
```
用户："在文档目录搜索report开头的文件"
调用：search_files(pattern="report.*", path="C:/Users/xxx/Documents")
```

### 场景4：统计文件数量
```
用户："文档目录有多少个文件"
调用：count_files(path="C:/Users/xxx/Documents")
```

### 场景5：查找大文件
```
用户："哪个文件夹最大"
调用：largest_folder(path="C:/Users/xxx", count=5)
```

### 场景6：列出目录内容
```
用户："列出文档目录的内容"
调用：list_directory(path="C:/Users/xxx/Documents")
```

## 返回信息

### disk_space返回
- 磁盘盘符（如C:、D:）
- 总容量
- 已使用空间
- 可用空间
- 使用百分比

### search_files返回
- 匹配的文件路径列表
- 文件大小
- 修改时间

### count_files返回
- 文件总数
- 文件夹总数
- 总大小

### largest_folder返回
- 文件夹路径
- 文件夹大小
- 文件数量

### list_directory返回
- 文件/文件夹名称
- 类型（文件/文件夹）
- 大小
- 修改时间

## 注意事项

### 1. 路径格式
- 支持绝对路径：`C:/Users/xxx/Documents`
- 支持相对路径：`./Documents`
- 支持用户目录：`~/Documents`
- 路径不存在时会提示用户

### 2. 搜索模式
- 支持通配符：`*`匹配任意字符，`?`匹配单个字符
- 支持正则表达式
- 不区分大小写

### 3. 权限问题
- 某些系统目录需要管理员权限
- 权限不足时会提示用户
- 建议在用户目录下操作

### 4. 搜索性能
- 大量文件搜索可能较慢
- 会提供进度反馈
- 可以通过指定路径缩小搜索范围

### 5. 隐藏文件
- 默认不显示隐藏文件
- 可以通过show_hidden参数显示
- Windows隐藏文件以`.`开头

## 常见问题

### Q1：如何搜索特定类型的文件？
A：使用通配符，例如：
```
search_files(pattern="*.pdf")  # 搜索所有PDF文件
search_files(pattern="*.docx")  # 搜索所有Word文档
```

### Q2：如何查找最近修改的文件？
A：使用list_directory查看修改时间，或使用search_files并按时间排序。

### Q3：可以搜索文件内容吗？
A：当前版本不支持文件内容搜索，只支持文件名搜索。

### Q4：权限不足怎么办？
A：尝试以管理员身份运行，或选择有权限的目录。

## 示例对话

### 示例1：查看磁盘空间
```
用户：查看磁盘空间
系统：磁盘使用情况：
- C:盘：总容量 500GB，已使用 350GB，可用 150GB（70%）
- D:盘：总容量 1TB，已使用 600GB，可用 400GB（60%）
```

### 示例2：搜索文件
```
用户：搜索所有PDF文件
系统：找到15个PDF文件：
- C:/Users/xxx/Documents/report1.pdf (2.5MB)
- C:/Users/xxx/Documents/report2.pdf (1.8MB)
- ...
```

### 示例3：查找大文件夹
```
用户：哪个文件夹最大
系统：最大的5个文件夹：
1. C:/Users/xxx/Videos - 50GB
2. C:/Users/xxx/Pictures - 30GB
3. C:/Users/xxx/Music - 20GB
4. C:/Users/xxx/Downloads - 15GB
5. C:/Users/xxx/Documents - 10GB
```

## 相关工具
- `query_tools`: 查询可用工具
- `send_email`: 发送邮件（可以将文件作为附件发送）
