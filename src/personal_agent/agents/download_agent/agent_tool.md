---
name: file_download
description: 文件下载管理工具，支持单文件和批量下载
version: 1.0.0
---

# 文件下载工具

## 功能说明
本工具用于下载文件，支持以下功能：
- 单文件下载
- 批量文件下载
- 断点续传
- 下载进度显示
- 下载速度统计

## 参数说明

### download（单文件下载）
- `url`: 下载地址
  - 类型：string
  - 示例："https://example.com/file.pdf"
  - 说明：必需参数

- `save_path`: 保存路径
  - 类型：string
  - 示例："C:/Users/xxx/Downloads/file.pdf"
  - 说明：可选参数，默认Downloads目录

- `filename`: 文件名
  - 类型：string
  - 示例："file.pdf"
  - 说明：可选参数，默认从URL提取

### batch_download（批量下载）
- `urls`: 地址列表
  - 类型：array
  - 示例：["https://example.com/file1.pdf", "https://example.com/file2.pdf"]
  - 说明：必需参数

- `save_dir`: 保存目录
  - 类型：string
  - 示例："C:/Users/xxx/Downloads"
  - 说明：可选参数，默认Downloads目录

- `max_concurrent`: 最大并发数
  - 类型：integer
  - 示例：3
  - 说明：可选参数，默认3个

### resume_download（断点续传）
- `url`: 下载地址
  - 类型：string
  - 示例："https://example.com/file.pdf"
  - 说明：必需参数

- `save_path`: 保存路径
  - 类型：string
  - 示例："C:/Users/xxx/Downloads/file.pdf"
  - 说明：必需参数

### check_download_status（检查下载状态）
- `task_id`: 任务ID
  - 类型：string
  - 示例："12345"
  - 说明：必需参数

### cancel_download（取消下载）
- `task_id`: 任务ID
  - 类型：string
  - 示例："12345"
  - 说明：必需参数

## 使用场景

### 场景1：单文件下载
```
用户："下载https://example.com/file.pdf"
调用：download(url="https://example.com/file.pdf")
```

### 场景2：指定保存路径下载
```
用户："下载文件到C:/Users/xxx/Documents"
调用：download(url="https://example.com/file.pdf", save_path="C:/Users/xxx/Documents/file.pdf")
```

### 场景3：批量下载
```
用户："批量下载这些文件"
调用：batch_download(urls=["https://example.com/file1.pdf", "https://example.com/file2.pdf"])
```

### 场景4：断点续传
```
用户："继续下载file.pdf"
调用：resume_download(url="https://example.com/file.pdf", save_path="C:/Users/xxx/Downloads/file.pdf")
```

### 场景5：检查下载状态
```
用户："下载进度怎么样"
调用：check_download_status(task_id="12345")
```

### 场景6：取消下载
```
用户："取消下载"
调用：cancel_download(task_id="12345")
```

## 返回信息

### download返回
- 任务ID
- 下载状态
- 文件保存路径
- 文件大小
- 下载速度

### batch_download返回
- 任务列表
- 总任务数
- 成功数
- 失败数

### resume_download返回
- 任务ID
- 下载状态
- 已下载大小
- 总大小
- 下载进度

### check_download_status返回
- 任务ID
- 下载状态
- 已下载大小
- 总大小
- 下载进度
- 下载速度
- 剩余时间

### cancel_download返回
- 任务ID
- 取消状态
- 已下载大小

## 注意事项

### 1. 网络连接
- 需要稳定的网络连接
- 网络中断时会暂停下载
- 支持断点续传

### 2. 文件覆盖
- 文件已存在时会询问是否覆盖
- 可以选择重命名或覆盖
- 建议先检查文件是否存在

### 3. 下载速度
- 下载速度受网络限制
- 大文件下载可能较慢
- 会显示下载进度和速度

### 4. 并发下载
- 批量下载时支持并发
- 默认最大并发数3
- 可以调整并发数

### 5. 下载失败
- 网络问题会提示重试
- URL错误会提示检查地址
- 权限问题会提示检查保存路径

## 常见问题

### Q1：下载的文件保存在哪里？
A：默认保存在Downloads目录，可以指定保存路径。

### Q2：如何断点续传？
A：使用resume_download，指定URL和保存路径即可。

### Q3：批量下载会同时进行吗？
A：是的，支持并发下载，默认最大并发数3。

### Q4：下载失败怎么办？
A：检查网络连接，确认URL正确，或稍后重试。

### Q5：可以限制下载速度吗？
A：当前版本不支持，后续版本会添加速度限制功能。

## 示例对话

### 示例1：单文件下载
```
用户：下载https://example.com/file.pdf
系统：正在下载...
下载完成：C:/Users/xxx/Downloads/file.pdf (2.5MB)
```

### 示例2：批量下载
```
用户：批量下载这些文件
系统：开始批量下载...
任务1：file1.pdf - 下载中 (50%)
任务2：file2.pdf - 等待中
任务3：file3.pdf - 等待中
...
```

### 示例3：检查下载状态
```
用户：下载进度怎么样
系统：下载状态：
- 任务ID：12345
- 状态：下载中
- 已下载：1.2GB / 2.5GB (48%)
- 速度：5.2MB/s
- 剩余时间：4分30秒
```

## 相关工具
- `query_tools`: 查询可用工具
- `file_management`: 文件管理（可以管理下载的文件）
- `web_crawler`: 网络爬虫（可以搜索下载链接）
