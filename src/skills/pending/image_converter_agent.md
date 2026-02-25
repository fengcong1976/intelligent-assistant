# Image Converter Agent

name: image_converter_agent
description: 图片格式转换智能体 - 支持多种图片格式之间的转换（PNG、JPG、WEBP、BMP、GIF等）
version: 1.0.0

## Capabilities

- convert: 转换图片格式
- resize: 调整图片尺寸
- batch_convert: 批量转换图片格式

## Keywords

- 图片转换
- 格式转换
- png转jpg
- jpg转png
- 转换图片
- 图片格式

## How to use

### 1. 转换图片格式

用户输入示例:
- "把这个png转成jpg"
- "转换图片格式为webp"
- "把图片转成png格式"

参数:
- source_path: 源图片路径 (必需)
- target_format: 目标格式，如 jpg, png, webp, bmp, gif (必需)
- quality: 图片质量 1-100，仅对 jpg/webp 有效 (可选，默认85)

### 2. 调整图片尺寸

用户输入示例:
- "把图片缩小到800x600"
- "调整图片尺寸"

参数:
- source_path: 源图片路径 (必需)
- width: 目标宽度 (可选)
- height: 目标高度 (可选)
- scale: 缩放比例，如 0.5 表示缩小一半 (可选)

### 3. 批量转换

用户输入示例:
- "批量转换这个文件夹里的png为jpg"

参数:
- source_dir: 源文件夹路径 (必需)
- target_format: 目标格式 (必需)

## Edge Cases

1. 源文件不存在: 返回错误提示
2. 不支持的格式: 返回支持的格式列表
3. 目标文件已存在: 自动添加后缀避免覆盖
4. 转换失败: 返回详细错误信息

## Implementation Notes

1. 使用 Pillow 库进行图片处理
2. 支持的格式: PNG, JPG/JPEG, WEBP, BMP, GIF, TIFF
3. JPG 转换时默认使用 RGB 模式（去除透明通道）
4. PNG 转换时保留透明通道
5. 输出文件保存在源文件同目录，文件名相同但扩展名改变
