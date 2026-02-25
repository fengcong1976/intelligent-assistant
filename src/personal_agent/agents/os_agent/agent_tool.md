---
name: system_control
description: 系统控制工具，包括音量、电源、网络等系统操作
version: 1.0.0
---

# 系统控制工具

## 功能说明
本工具用于控制系统设置，支持以下功能：
- 音量控制（系统音量）
- 电源控制（睡眠、关机、重启）
- WiFi管理（连接、断开、查看状态）
- 亮度调节
- 屏幕控制

## 参数说明

### volume_set（设置音量）
- `value`: 音量值
  - 类型：integer
  - 示例：50
  - 说明：必需参数，范围0-100

### volume_mute（静音）
- 无参数

### volume_unmute（取消静音）
- 无参数

### volume_up（增大音量）
- 无参数

### volume_down（减小音量）
- 无参数

### sleep（睡眠）
- 无参数

### shutdown（关机）
- `delay`: 延迟时间（秒）
  - 类型：integer
  - 示例：60
  - 说明：可选参数，默认立即关机

### restart（重启）
- `delay`: 延迟时间（秒）
  - 类型：integer
  - 示例：60
  - 说明：可选参数，默认立即重启

### wifi_list（列出WiFi）
- 无参数

### wifi_connect（连接WiFi）
- `name`: WiFi名称
  - 类型：string
  - 示例："MyWiFi"
  - 说明：必需参数

- `password`: WiFi密码
  - 类型：string
  - 示例："password123"
  - 说明：可选参数

### wifi_disconnect（断开WiFi）
- 无参数

### wifi_status（WiFi状态）
- 无参数

### brightness_set（设置亮度）
- `value`: 亮度值
  - 类型：integer
  - 示例：80
  - 说明：必需参数，范围0-100

### brightness_up（增大亮度）
- 无参数

### brightness_down（减小亮度）
- 无参数

## 使用场景

### 场景1：音量控制
```
用户："调大音量"
调用：volume_up()

用户："静音"
调用：volume_mute()

用户："设置音量为50"
调用：volume_set(value=50)
```

### 场景2：电源控制
```
用户："睡眠"
调用：sleep()

用户："关机"
调用：shutdown()

用户："重启"
调用：restart()
```

### 场景3：WiFi管理
```
用户："列出WiFi"
调用：wifi_list()

用户："连接MyWiFi"
调用：wifi_connect(name="MyWiFi", password="password123")
```

### 场景4：亮度调节
```
用户："调大亮度"
调用：brightness_up()

用户："设置亮度为80"
调用：brightness_set(value=80)
```

## 返回信息

### volume_set返回
- 当前音量
- 设置状态

### volume_mute/unmute返回
- 静音状态
- 操作结果

### volume_up/down返回
- 当前音量
- 音量变化

### sleep返回
- 睡眠状态
- 操作结果

### shutdown/restart返回
- 操作状态
- 延迟时间

### wifi_list返回
- WiFi列表
- 信号强度
- 安全状态

### wifi_connect返回
- 连接状态
- WiFi名称
- IP地址

### wifi_disconnect返回
- 断开状态
- WiFi名称

### wifi_status返回
- 当前WiFi名称
- 连接状态
- 信号强度
- IP地址

### brightness_set返回
- 当前亮度
- 设置状态

### brightness_up/down返回
- 当前亮度
- 亮度变化

## 注意事项

### 1. 权限问题
- 某些操作需要管理员权限
- 权限不足时会提示用户
- 建议以管理员身份运行

### 2. 操作不可逆
- 关机、重启等操作不可逆
- 会确认用户意图
- 建议保存重要文件

### 3. 设备支持
- 部分功能依赖设备支持
- 不支持的功能会提示用户
- 不同设备功能可能不同

### 4. WiFi连接
- 需要正确的WiFi名称和密码
- 连接失败时会提示原因
- 支持自动重连

### 5. 音量和亮度
- 音量范围：0-100
- 亮度范围：0-100
- 超出范围会自动调整

## 常见问题

### Q1：如何取消关机？
A：关机操作会延迟执行，在延迟时间内可以取消。

### Q2：WiFi连接失败怎么办？
A：检查WiFi名称和密码是否正确，或尝试其他WiFi。

### Q3：音量控制针对哪个设备？
A：针对系统音量，不是播放器音量。

### Q4：亮度调节不生效怎么办？
A：检查设备是否支持亮度调节，或检查驱动程序。

## 示例对话

### 示例1：音量控制
```
用户：调大音量
系统：音量已调至 60%
```

### 示例2：WiFi连接
```
用户：连接MyWiFi
系统：正在连接MyWiFi...
连接成功：IP地址 192.168.1.100
```

### 示例3：亮度调节
```
用户：调大亮度
系统：亮度已调至 80%
```

## 相关工具
- `query_tools`: 查询可用工具
