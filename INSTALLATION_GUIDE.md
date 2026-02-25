# 创炫互动智能助理系统 - 安装使用说明

## 目录

- [系统要求](#系统要求)
- [安装步骤](#安装步骤)
- [配置说明](#配置说明)
- [使用指南](#使用指南)
- [常见问题](#常见问题)
- [技术支持](#技术支持)

---

## 系统要求

### 硬件要求

| 组件 | 最低要求 | 推荐配置 |
|------|----------|----------|
| CPU | 双核 2.0GHz | 四核 3.0GHz+ |
| 内存 | 4GB | 8GB+ |
| 硬盘 | 2GB可用空间 | 5GB+ SSD |
| 网络 | 宽带连接 | 稳定宽带 |

### 软件要求

| 软件 | 版本要求 | 说明 |
|------|----------|------|
| Python | 3.10+ | 必须，推荐3.11或3.12 |
| Windows | 10/11 | 推荐Windows 11 |
| 浏览器 | Chrome/Edge | 用于Web界面 |

### 必需账号

- **阿里云账号**: 用于通义千问（DashScope）API
  - 注册地址: https://dashscope.console.aliyun.com/
  - 需要开通DashScope服务
  - 获取API Key

---

## 安装步骤

### 第一步：下载项目

#### 方式1：从发布包安装（推荐）

1. 下载发布包 `personal-agent-v1.0.zip`
2. 解压到目标目录，例如：`D:\personal-agent`

#### 方式2：从源码安装

```bash
# 克隆仓库
git clone https://github.com/your-repo/personal-agent.git
cd personal-agent
```

### 第二步：安装Python环境

#### 方式1：使用系统Python（推荐）

1. 下载Python 3.11+: https://www.python.org/downloads/
2. 安装时勾选 "Add Python to PATH"
3. 验证安装：
```bash
python --version
# 输出: Python 3.11.x
```

#### 方式2：使用Anaconda

```bash
# 创建虚拟环境
conda create -n personal-agent python=3.11
conda activate personal-agent
```

### 第三步：安装依赖

```bash
# 进入项目目录
cd D:\personal-agent

# 安装依赖（完整安装）
pip install -r requirements.txt

# 或者最小安装（仅核心功能）
pip install dashscope PyQt6 aiohttp loguru pydantic pydantic-settings python-dotenv
```

**依赖安装说明**:

| 依赖类型 | 命令 | 说明 |
|----------|------|------|
| 完整安装 | `pip install -r requirements.txt` | 包含所有可选功能 |
| 最小安装 | 见上方命令 | 仅核心功能 |
| GUI版本 | `pip install PyQt6 PyQtWebEngine` | 需要图形界面 |
| Web版本 | `pip install fastapi uvicorn` | 需要Web服务 |
| 语音功能 | `pip install pyaudio SpeechRecognition pyttsx3` | 需要语音交互 |

### 第四步：配置环境变量

1. 复制环境变量模板：
```bash
copy .env.example .env
```

2. 编辑 `.env` 文件，填写必要配置：

```ini
# ========== 大模型配置 ==========
# 模型提供商（只支持dashscope）
LLM_PROVIDER=dashscope

# 通义千问 API Key（必须）
DASHSCOPE_API_KEY=sk-your-api-key-here
DASHSCOPE_MODEL=qwen-plus
DASHSCOPE_ENABLE_SEARCH=true

# ========== 语音配置 ==========
# 语音识别引擎
VOICE_PROVIDER=dashscope
VOICE_DASHSCOPE_API_KEY=sk-your-api-key-here

# 语音合成
TTS_ENABLED=true
TTS_VOICE=longyue_v3
TTS_SPEECH_RATE=1.0

# ========== 用户信息 ==========
USER_NAME=用户
USER_CITY=北京

# ========== 智能体配置 ==========
AGENT_NAME=小助手
AGENT_GENDER=女
AGENT_VOICE=温柔
AGENT_PERSONALITY=友好、专业、乐于助人

# ========== 目录配置 ==========
MUSIC_LIBRARY_PATH=D:\Music
DOWNLOAD_DIR=D:\Downloads
DOCUMENTS_DIR=D:\Documents
PICTURES_DIR=D:\Pictures

# ========== 安全配置 ==========
ALLOWED_DIRECTORIES=D:\,E:\
DANGEROUS_COMMANDS=rm -rf,format,del /s

# ========== 日志配置 ==========
LOG_LEVEL=INFO
```

### 第五步：获取API Key

#### 获取阿里云DashScope API Key

1. 访问阿里云控制台: https://dashscope.console.aliyun.com/
2. 登录/注册阿里云账号
3. 开通DashScope服务
4. 创建API Key:
   - 点击左侧菜单 "API-KEY管理"
   - 点击 "创建新的API-KEY"
   - 复制生成的API Key（格式：sk-xxxxxxxxxxxx）
5. 将API Key填入 `.env` 文件的 `DASHSCOPE_API_KEY`

**注意**: 
- 新用户有免费额度
- API Key请妥善保管，不要泄露
- 建议设置使用限额

### 第六步：验证安装

```bash
# 运行测试
python -c "from personal_agent.config import settings; print('✅ 配置加载成功')"
python -c "import dashscope; print('✅ DashScope SDK已安装')"
python -c "from PyQt6.QtWidgets import QApplication; print('✅ PyQt6已安装')"
```

---

## 配置说明

### 大模型配置

| 配置项 | 说明 | 默认值 | 可选值 |
|--------|------|--------|--------|
| LLM_PROVIDER | 模型提供商 | dashscope | dashscope |
| DASHSCOPE_API_KEY | API密钥 | - | 必须填写 |
| DASHSCOPE_MODEL | 模型名称 | qwen-plus | qwen-turbo, qwen-plus, qwen-max |
| DASHSCOPE_ENABLE_SEARCH | 启用联网搜索 | true | true, false |

**模型选择建议**:
- **qwen-turbo**: 快速响应，适合简单对话
- **qwen-plus**: 平衡性能，推荐日常使用
- **qwen-max**: 最强能力，适合复杂任务

### 语音配置

| 配置项 | 说明 | 默认值 | 可选值 |
|--------|------|--------|--------|
| VOICE_PROVIDER | 语音识别引擎 | dashscope | dashscope, funasr, speech_recognition |
| TTS_ENABLED | 启用语音合成 | true | true, false |
| TTS_VOICE | 语音角色 | longyue_v3 | 见下表 |
| TTS_SPEECH_RATE | 语速 | 1.0 | 0.5-2.0 |

**语音角色列表**:
| 角色 | 名称 | 特点 |
|------|------|------|
| longyue_v3 | 龙悦v3 | 活力女声 |
| longyingjing_v3 | 龙盈京v3 | 京味女声 |
| longfei_v3 | 龙飞v3 | 磁性男声 |
| longshuo_v3 | 龙硕v3 | 沉稳男声 |
| longjielidou_v3 | 龙杰力豆v3 | 童声 |

### 目录配置

| 配置项 | 说明 | 示例 |
|--------|------|------|
| MUSIC_LIBRARY_PATH | 音乐库路径 | D:\Music |
| DOWNLOAD_DIR | 下载目录 | D:\Downloads |
| DOCUMENTS_DIR | 文档目录 | D:\Documents |
| PICTURES_DIR | 图片目录 | D:\Pictures |

**注意**: 
- 路径不要包含中文和特殊字符
- 确保目录存在且有读写权限
- 使用绝对路径

### 安全配置

| 配置项 | 说明 | 示例 |
|--------|------|------|
| ALLOWED_DIRECTORIES | 允许访问的目录 | D:\,E:\ |
| DANGEROUS_COMMANDS | 危险命令黑名单 | rm -rf,format |

---

## 使用指南

### 启动程序

#### 方式1：图形界面版本（推荐）

```bash
# 方式1：直接运行
python run_gui.py

# 方式2：使用启动脚本
python start_gui.py
```

#### 方式2：命令行版本

```bash
python main.py
```

#### 方式3：Web版本

```bash
# 启动Web服务
python start_web.py

# 或简化版本
python start_web_simple.py

# 访问 http://localhost:8000
```

### 图形界面使用

#### 主界面介绍

```
┌─────────────────────────────────────────────────────────────┐
│  创炫互动智能助理                              [─] [□] [×]   │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐   │
│  │                                                     │   │
│  │  对话区域                                            │   │
│  │  显示对话历史                                        │   │
│  │                                                     │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ [🎤] [输入消息...]                          [发送]   │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐            │
│  │ 音乐 │ │ 视频 │ │ 邮件 │ │ 天气 │ │ 设置 │            │
│  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘            │
└─────────────────────────────────────────────────────────────┘
```

#### 快捷键

| 快捷键 | 功能 |
|--------|------|
| Enter | 发送消息 |
| Ctrl+Enter | 换行 |
| Ctrl+N | 新建对话 |
| Ctrl+S | 保存对话 |
| Ctrl+, | 打开设置 |
| F11 | 全屏模式 |

#### 语音交互

1. **语音输入**:
   - 点击麦克风图标 🎤
   - 开始说话
   - 再次点击或等待自动结束
   - 系统自动识别并处理

2. **语音输出**:
   - 在设置中启用语音合成
   - 系统会自动朗读回复内容

### 常用功能

#### 1. 音乐播放

```
用户: 播放音乐
用户: 播放周杰伦的歌曲
用户: 暂停
用户: 下一首
用户: 扫描音乐库
```

#### 2. 视频播放

```
用户: 播放视频
用户: 看电影
用户: 打开D:\Videos\movie.mp4
```

#### 3. 天气查询

```
用户: 今天天气
用户: 北京明天天气
用户: 上海后天天气预报
```

#### 4. 邮件管理

```
用户: 发送邮件
用户: 给张三发邮件
用户: 查看邮件
```

#### 5. 文件管理

```
用户: 搜索文件
用户: 查找D盘的PDF文件
用户: 查看磁盘空间
```

#### 6. 系统控制

```
用户: 系统关机
用户: 电脑重启
用户: 截屏
用户: 查看系统信息
```

#### 7. 应用管理

```
用户: 打开QQ音乐
用户: 启动浏览器
用户: 安装应用
```

### 快速跳转关键词

系统支持关键词快速跳转，无需等待LLM分析：

| 智能体 | 关键词 |
|--------|--------|
| 音乐智能体 | 播放音乐、播放歌曲、放首歌 |
| 视频智能体 | 播放视频、看电影、放电影 |
| 系统智能体 | 系统关机、电脑关机、关电脑 |
| 邮件智能体 | 发送邮件、发邮件、写邮件 |
| 天气智能体 | 查天气、天气预报、今天天气 |
| 文件智能体 | 搜索文件、查找文件 |
| 新闻智能体 | 查看新闻、最新新闻 |

### 设置界面

点击"设置"按钮或按 `Ctrl+,` 打开设置界面：

#### 用户信息标签

- 用户姓名
- 正式称呼
- 邮箱地址
- 电话号码
- 所在城市

#### 智能体设置标签

- 智能体名称
- 性别
- 语音风格
- 性格特点
- 问候语

#### 大模型设置标签

- API Key配置
- 模型选择
- 联网搜索开关
- 语音识别设置
- 语音合成设置

#### 目录设置标签

- 音乐库路径
- 下载目录
- 文档目录
- 图片目录

---

## 常见问题

### 安装问题

#### Q1: pip安装依赖失败

**问题**: `pip install -r requirements.txt` 报错

**解决方案**:
```bash
# 升级pip
python -m pip install --upgrade pip

# 使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 或逐个安装
pip install dashscope PyQt6 aiohttp loguru
```

#### Q2: PyQt6安装失败

**问题**: PyQt6安装报错

**解决方案**:
```bash
# 使用conda安装
conda install pyqt

# 或从PyPI安装
pip install PyQt6 -i https://pypi.org/simple
```

#### Q3: Python版本不兼容

**问题**: 提示Python版本过低

**解决方案**:
- 升级Python到3.10+
- 或使用pyenv/conda管理多版本Python

### 配置问题

#### Q4: API Key无效

**问题**: 提示"API Key无效"

**解决方案**:
1. 检查API Key格式（应以sk-开头）
2. 确认API Key未过期
3. 检查是否开通DashScope服务
4. 确认账户有余额或免费额度

#### Q5: 配置文件找不到

**问题**: 提示".env文件不存在"

**解决方案**:
```bash
# 复制模板文件
copy .env.example .env

# 编辑配置
notepad .env
```

### 运行问题

#### Q6: 程序启动失败

**问题**: 运行 `python run_gui.py` 报错

**解决方案**:
```bash
# 检查依赖
pip list | findstr PyQt6

# 重新安装PyQt6
pip uninstall PyQt6
pip install PyQt6

# 检查Python版本
python --version
```

#### Q7: 语音识别不工作

**问题**: 点击麦克风没有反应

**解决方案**:
1. 检查麦克风权限
2. 安装音频依赖：
```bash
pip install pyaudio
```
3. 检查API Key配置
4. 尝试其他识别引擎

#### Q8: 音乐播放失败

**问题**: 提示"无法播放音乐"

**解决方案**:
1. 检查音乐库路径配置
2. 确认音乐文件格式支持（MP3, WAV, FLAC）
3. 安装VLC或使用系统播放器
4. 检查文件权限

### 性能问题

#### Q9: 响应速度慢

**问题**: AI回复很慢

**解决方案**:
1. 使用快速跳转关键词
2. 切换到qwen-turbo模型
3. 检查网络连接
4. 减少对话历史长度

#### Q10: 内存占用高

**问题**: 程序占用内存过大

**解决方案**:
1. 关闭不需要的功能
2. 减少历史记录保存天数
3. 定期清理缓存
4. 重启程序

---

## 技术支持

### 获取帮助

1. **查看文档**:
   - 项目总结: `docs/PROJECT_SUMMARY.md`
   - 对比分析: `docs/COMPARISON_WITH_OPENCLAW.md`

2. **查看日志**:
   - 日志位置: `logs/` 目录
   - 日志级别可在 `.env` 中配置

3. **提交问题**:
   - GitHub Issues: https://github.com/your-repo/personal-agent/issues
   - 提供详细错误信息和日志

### 日志查看

```bash
# 查看最新日志
type logs\app.log

# 查看错误日志
findstr "ERROR" logs\app.log
```

### 重置配置

```bash
# 删除配置文件
del .env
del data\user_config.json

# 重新生成
copy .env.example .env
```

---

## 附录

### A. 完整配置文件示例

```ini
# ========== 大模型配置 ==========
LLM_PROVIDER=dashscope
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxx
DASHSCOPE_MODEL=qwen-plus
DASHSCOPE_ENABLE_SEARCH=true

# ========== 语音配置 ==========
VOICE_PROVIDER=dashscope
VOICE_DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxx
TTS_ENABLED=true
TTS_VOICE=longyue_v3
TTS_SPEECH_RATE=1.0

# ========== 用户信息 ==========
USER_NAME=张三
USER_FORMAL_NAME=张先生
USER_EMAIL=zhangsan@example.com
USER_PHONE=13800138000
USER_ADDRESS=北京市朝阳区
USER_CITY=北京
USER_TIMEZONE=Asia/Shanghai

# ========== 智能体配置 ==========
AGENT_NAME=小助手
AGENT_GENDER=女
AGENT_VOICE=温柔
AGENT_PERSONALITY=友好、专业、乐于助人
AGENT_GREETING=您好！我是您的智能助手，有什么可以帮助您的吗？
AGENT_MAX_ITERATIONS=10
AGENT_TIMEOUT=300

# ========== 目录配置 ==========
MUSIC_LIBRARY_PATH=D:\Music
DOWNLOAD_DIR=D:\Downloads
DOCUMENTS_DIR=D:\Documents
PICTURES_DIR=D:\Pictures

# ========== 安全配置 ==========
ALLOWED_DIRECTORIES=D:\,E:\
DANGEROUS_COMMANDS=rm -rf,format,del /s

# ========== 日志配置 ==========
LOG_LEVEL=INFO
LOG_FILE=logs/app.log

# ========== 邮件配置（可选） ==========
AGENT_EMAIL=your-email@example.com
AGENT_EMAIL_PASSWORD=your-password
AGENT_EMAIL_SMTP=smtp.example.com
AGENT_EMAIL_PORT=587

# ========== HomeAssistant配置（可选） ==========
HOMEASSISTANT_ENABLED=false
HOMEASSISTANT_URL=http://localhost:8123
HOMEASSISTANT_TOKEN=your-token

# ========== 股票配置（可选） ==========
TUSHARE_TOKEN=your-tushare-token
```

### B. 依赖包列表

| 包名 | 版本 | 用途 |
|------|------|------|
| dashscope | >=1.14.0 | 阿里云SDK |
| PyQt6 | >=6.6.0 | GUI界面 |
| aiohttp | >=3.9.0 | 异步HTTP |
| loguru | >=0.7.0 | 日志 |
| pydantic | >=2.0.0 | 数据验证 |
| python-dotenv | >=1.0.0 | 环境变量 |
| pyaudio | >=0.2.13 | 音频录制 |
| SpeechRecognition | >=3.10.0 | 语音识别 |
| pyttsx3 | >=2.90 | 语音合成 |
| reportlab | >=4.0.0 | PDF生成 |
| python-docx | >=1.0.0 | Word文档 |
| openpyxl | >=3.1.0 | Excel处理 |
| Pillow | >=10.0.0 | 图片处理 |

### C. 支持的音频格式

| 格式 | 播放 | 识别 | 说明 |
|------|------|------|------|
| MP3 | ✅ | ✅ | 推荐 |
| WAV | ✅ | ✅ | 无损 |
| FLAC | ✅ | ✅ | 无损压缩 |
| AAC | ✅ | ❌ | 需转换 |
| OGG | ✅ | ❌ | 需转换 |

---

**文档版本**: v1.0  
**最后更新**: 2026年2月25日  
**作者**: 创炫互动开发团队
