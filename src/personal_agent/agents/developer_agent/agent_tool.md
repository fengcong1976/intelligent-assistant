---
name: code_development
description: 代码开发工具，支持代码生成、修改、审查
version: 1.0.0
---

# 代码开发工具

## 功能说明
本工具用于辅助代码开发，支持以下功能：
- 代码生成（根据功能描述）
- 代码修改
- 代码审查
- 创建新模块
- 代码优化建议

## 参数说明

### generate_code（生成代码）
- `description`: 功能描述
  - 类型：string
  - 示例："创建一个计算斐波那契数列的函数"
  - 说明：必需参数

- `language`: 编程语言
  - 类型：string
  - 示例："Python"、"JavaScript"、"Java"
  - 说明：可选参数，默认Python

- `file_path`: 文件路径
  - 类型：string
  - 示例："fibonacci.py"
  - 说明：可选参数，用于保存代码

### modify_code（修改代码）
- `file_path`: 文件路径
  - 类型：string
  - 示例："fibonacci.py"
  - 说明：必需参数

- `changes`: 修改内容
  - 类型：string
  - 示例："添加错误处理"
  - 说明：必需参数

- `line_number`: 行号
  - 类型：integer
  - 示例：10
  - 说明：可选参数，指定修改位置

### review_code（审查代码）
- `file_path`: 文件路径
  - 类型：string
  - 示例："fibonacci.py"
  - 说明：必需参数

- `focus`: 审查重点
  - 类型：string
  - 示例："性能"、"安全性"、"可读性"
  - 说明：可选参数

### create_module（创建模块）
- `name`: 模块名
  - 类型：string
  - 示例："utils"
  - 说明：必需参数

- `type`: 模块类型
  - 类型：string
  - 示例："class"、"function"、"module"
  - 说明：可选参数

- `description`: 模块描述
  - 类型：string
  - 示例："工具函数集合"
  - 说明：可选参数

### optimize_code（优化代码）
- `file_path`: 文件路径
  - 类型：string
  - 示例："fibonacci.py"
  - 说明：必需参数

- `focus`: 优化重点
  - 类型：string
  - 示例："性能"、"内存"、"可读性"
  - 说明：可选参数

## 使用场景

### 场景1：生成代码
```
用户："帮我写一个计算斐波那契数列的函数"
调用：generate_code(description="创建一个计算斐波那契数列的函数", language="Python")
```

### 场景2：修改代码
```
用户："在fibonacci.py中添加错误处理"
调用：modify_code(file_path="fibonacci.py", changes="添加错误处理")
```

### 场景3：审查代码
```
用户："审查fibonacci.py的代码"
调用：review_code(file_path="fibonacci.py")
```

### 场景4：创建模块
```
用户："创建一个名为utils的工具模块"
调用：create_module(name="utils", type="module", description="工具函数集合")
```

### 场景5：优化代码
```
用户："优化fibonacci.py的性能"
调用：optimize_code(file_path="fibonacci.py", focus="性能")
```

## 返回信息

### generate_code返回
- 生成的代码
- 代码说明
- 使用示例
- 注意事项

### modify_code返回
- 修改后的代码
- 修改说明
- 影响范围

### review_code返回
- 代码质量评分
- 发现的问题
- 改进建议
- 最佳实践建议

### create_module返回
- 模块代码
- 模块结构
- 使用说明

### optimize_code返回
- 优化后的代码
- 优化说明
- 性能对比
- 改进建议

## 注意事项

### 1. 代码执行风险
- 生成和修改的代码不会自动执行
- 用户需要手动测试
- 执行前建议先审查

### 2. 文件操作
- 文件不存在时会询问是否创建
- 文件已存在时会询问是否覆盖
- 建议先备份原文件

### 3. 代码质量
- 生成的代码遵循最佳实践
- 包含必要的注释
- 包含错误处理

### 4. 依赖管理
- 如果代码需要外部依赖，会提示用户
- 建议使用虚拟环境
- 提供依赖安装命令

### 5. 代码审查
- 审查基于静态分析
- 不包含动态测试
- 建议结合测试工具

## 常见问题

### Q1：生成的代码可以直接使用吗？
A：生成的代码需要用户测试和调整，建议先审查再使用。

### Q2：如何修改特定行的代码？
A：使用modify_code并指定line_number参数。

### Q3：代码审查包含哪些内容？
A：包含代码质量、安全性、性能、可读性等方面的检查。

### Q4：可以生成任何语言的代码吗？
A：支持主流编程语言，包括Python、JavaScript、Java、C++等。

## 示例对话

### 示例1：生成代码
```
用户：帮我写一个计算斐波那契数列的函数
系统：已生成Python代码：

def fibonacci(n):
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    else:
        return fibonacci(n-1) + fibonacci(n-2)

使用示例：
print(fibonacci(10))  # 输出：55
```

### 示例2：审查代码
```
用户：审查fibonacci.py的代码
系统：代码审查结果：
- 代码质量：良好
- 问题：递归实现可能导致性能问题
- 建议：使用迭代实现提高性能
```

### 示例3：优化代码
```
用户：优化fibonacci.py的性能
系统：优化后的代码：

def fibonacci(n):
    if n <= 0:
        return 0
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a

性能提升：从O(2^n)优化到O(n)
```

## 相关工具
- `query_tools`: 查询可用工具
- `file_management`: 文件管理（可以保存代码文件）
