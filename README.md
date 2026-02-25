# 创炫互动智能助理系统

一个基于Python和PyQt6的个人智能助理系统，支持自然语言交互、多智能体协作、快速响应等功能。

## 功能特性

- 🎵 **音乐播放**：支持本地音乐库管理、播放控制、歌曲搜索
- 🎬 **视频播放**：支持本地视频播放、在线视频播放、投屏功能
- 📧 **邮件管理**：支持邮件发送、接收、附件处理
- 🌤️ **天气查询**：实时天气查询、天气预报
- 📈 **股票查询**：实时股票行情、指数查询、K线图
- 🛒 **购物助手**：商品搜索、价格比较、购物清单管理
- 🏠 **智能家居**：HomeAssistant集成、设备控制
- 🖥️ **系统控制**：音量控制、屏幕截图、系统关机等
- 📅 **日程管理**：日历查看、日程安排
- 🗺️ **旅游规划**：智能旅游攻略生成
- 🎨 **图片生成**：AI图片生成
- 🔍 **网络搜索**：网络搜索、新闻查询
- 📁 **文件管理**：文件下载、格式转换
- 💻 **开发任务**：代码生成、命令执行

## 技术栈

- **Python** 3.10+
- **PyQt6**：GUI界面
- **异步架构**：asyncio支持
- **阿里云通义千问**：LLM支持
- **FastAPI**：Web服务
- **模块化设计**：智能体独立开发、独立部署

## 安装

### 环境要求

- Python 3.10 或更高版本
- Windows 10/11 或 Linux

### 安装步骤

1. 克隆仓库
```bash
git clone https://gitee.com/your-username/personal-agent.git
cd personal-agent
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 配置环境变量

复制 `.env.example` 为 `.env`，并填写配置信息：
```env
# LLM配置
DASHSCOPE_API_KEY=your_api_key_here

# 邮件配置
EMAIL_SMTP_SERVER=smtp.qq.com
EMAIL_SMTP_PORT=587
EMAIL_USERNAME=your_email@qq.com
EMAIL_PASSWORD=your_password

# 音乐库路径
MUSIC_LIBRARY_PATH=E:/Music

# 视频库路径
VIDEO_LIBRARY_PATH=E:/Videos
```

4. 运行程序
```bash
python main.py
```

## 使用方法

### GUI界面

启动程序后，会显示图形界面，可以直接在对话框中输入指令：

```
播放周杰伦的歌
今天天气怎么样
发送邮件给张三
生成一张荷花照片
```

### CLI模式

```bash
python main.py --cli
```

### Web服务

```bash
python main.py --web
```

## 项目结构

```
personal-agent/
├── src/
│   └── personal_agent/
│       ├── agents/          # 智能体模块
│       │   ├── master.py   # 主智能体
│       │   ├── music_agent/
│       │   ├── video_agent/
│       │   └── ...
│       ├── channels/        # 交互通道
│       ├── intent/         # 意图解析
│       ├── llm/           # LLM接口
│       ├── tools/          # 工具注册
│       └── utils/         # 工具函数
├── docs/                 # 文档
├── tests/                # 测试
├── main.py              # 主程序入口
└── requirements.txt     # 依赖列表
```

## 智能体列表

| 智能体 | 功能 |
|--------|------|
| master | 主智能体，负责任务分发和协调 |
| music_agent | 音乐播放和管理 |
| video_agent | 视频播放和管理 |
| email_agent | 邮件发送和接收 |
| weather_agent | 天气查询 |
| stock_query_agent | 股票查询 |
| shopping_agent | 购物助手 |
| home_assistant_agent | 智能家居控制 |
| os_agent | 系统控制 |
| calendar_agent | 日程管理 |
| travel_agent | 旅游规划 |
| image_agent | 图片生成 |
| web_search_agent | 网络搜索 |
| file_agent | 文件管理 |
| developer_agent | 开发任务 |

## 快速开始

### 播放音乐

```
播放周杰伦的歌
下一首
暂停音乐
```

### 查询天气

```
今天天气
明天北京天气
```

### 发送邮件

```
发送邮件给张三，内容是你好
```

### 生成图片

```
生成一张荷花照片
生成一张1920*1080的风景图
```

### 系统控制

```
关机
重启
截图
```

## 配置说明

### LLM配置

支持阿里云通义千问（DashScope）：

```env
DASHSCOPE_API_KEY=your_api_key_here
```

### 邮件配置

```env
EMAIL_SMTP_SERVER=smtp.qq.com
EMAIL_SMTP_PORT=587
EMAIL_USERNAME=your_email@qq.com
EMAIL_PASSWORD=your_password
EMAIL_IMAP_SERVER=imap.qq.com
EMAIL_IMAP_PORT=993
```

### 音乐库配置

```env
MUSIC_LIBRARY_PATH=E:/Music
```

## 开发

### 添加新智能体

1. 在 `src/personal_agent/agents/` 下创建新目录
2. 继承 `BaseAgent` 类
3. 实现 `execute_task` 方法
4. 注册工具和别名

### 运行测试

```bash
pytest tests/
```

## 文档

详细文档请查看 [docs](docs/) 目录：

- [项目总结](docs/PROJECT_SUMMARY.md)
- [与OpenClaw对比](docs/COMPARISON_WITH_OPENCLAW.md)
- [安装指南](docs/INSTALLATION_GUIDE.md)

## 贡献

欢迎提交Issue和Pull Request！

## 许可证

MIT License

## 联系方式

- 项目地址：[Gitee](https://gitee.com/your-username/personal-agent)
- 问题反馈：[Issues](https://gitee.com/your-username/personal-agent/issues)

## 致谢

感谢以下开源项目的支持：
- PyQt6
- FastAPI
- 阿里云通义千问
- HomeAssistant
