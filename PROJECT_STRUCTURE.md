# 项目结构说明

```
创炫互动智能助理系统/
├── src/                      # 源代码目录
│   └── personal_agent/        # 核心代码
│       ├── agents/            # 智能体实现
│       ├── skills/            # 技能实现
│       ├── tools/            # 工具实现
│       ├── intent/            # 意图识别
│       ├── memory/            # 记忆系统
│       └── config/           # 配置管理
├── skills/                   # 技能目录
├── docs/                     # 文档目录
├── vlc_libs/                 # VLC库文件
├── data/                     # 数据目录
│   ├── history/              # 历史记录
│   ├── conversations/        # 对话记录
│   ├── contacts.json         # 联系人
│   └── user_config.json      # 用户配置
├── output/                   # 输出目录
│   ├── pdf/                  # PDF文件
│   ├── word/                 # Word文件
│   ├── excel/                # Excel文件
│   └── images/               # 图片文件
├── logs/                     # 日志目录
├── main.py                   # 命令行入口
├── run_gui.py                # GUI入口
├── start_web.py              # Web入口
├── pyproject.toml            # 项目配置
├── requirements.txt          # 依赖列表
├── .env.example              # 环境变量示例
├── README.md                 # 项目说明
├── RELEASE_NOTES.md          # 发布说明
└── .gitignore               # Git忽略文件
```

## 目录说明

### src/
源代码目录，包含所有核心代码。

### skills/
技能目录，包含可插拔的技能模块。

### docs/
文档目录，包含项目文档。

### vlc_libs/
VLC媒体播放器库文件。

### data/
数据目录，存储用户数据和历史记录。

### output/
输出目录，存储生成的文件（PDF、Word、Excel、图片等）。

### logs/
日志目录，存储运行日志。

### 配置文件
- `main.py`: 命令行版本入口
- `run_gui.py`: GUI版本入口
- `start_web.py`: Web版本入口
- `pyproject.toml`: 项目配置文件
- `requirements.txt`: Python依赖列表
- `.env.example`: 环境变量配置示例
- `README.md`: 项目说明文档
- `RELEASE_NOTES.md`: 发布说明
- `.gitignore`: Git忽略文件配置
