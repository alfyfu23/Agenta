# Agenta - 智能会议纪要生成系统

基于 Vue 3 + Flask + FunASR 的智能会议纪要生成系统，支持音频上传、语音转写、AI 校对与摘要生成。

## 项目结构

```
├── main.py                       # Flask 后端主入口
├── combined_transcription.py     # 语音转写 + AI 校对（完整流程）
├── transcription.py              # AI 文本校对（独立调用）
├── SenseVoiceSmall.py            # SenseVoice 语音转写（独立调用）
├── summary.py                    # 会议纪要生成（要点提取 + 模板填充）
├── prompt_tra.txt                # 转写校对 Prompt
├── ex_prompt_project.txt         # 项目进度会议要点提取 Prompt
├── ex_prompt_problem.txt         # 问题讨论会议要点提取 Prompt
├── ex_prompt_study.txt           # 学习讲座会议要点提取 Prompt
├── ex_prompt_custom.txt          # 自定义会议要点提取 Prompt
├── template_project.md           # 项目进度会议纪要模板
├── template_problem.md           # 问题讨论会议纪要模板
├── template_study.md             # 学习讲座会议纪要模板
├── custom.md                     # 自定义会议纪要模板
├── src/                          # Vue 3 前端源码
│   ├── App.vue                   # 根组件（侧边栏 + 顶部步骤条）
│   ├── main.js                   # 路由配置与入口
│   ├── style.css                 # Tailwind 全局样式
│   └── views/
│       ├── UploadPage.vue        # 音频上传页
│       ├── TranscriptionPage.vue # 转写进度与结果页
│       ├── TemplatesPage.vue     # 会议信息与模板选择页
│       └── ResultPage.vue        # 纪要展示与 AI 辅助编辑页
├── index.html                    # HTML 入口
├── vite.config.js                # Vite 配置（含 API 代理）
├── tailwind.config.js            # Tailwind CSS 配置
├── postcss.config.js             # PostCSS 配置
├── package.json                  # 前端依赖
├── start.sh                      # Linux/macOS 启动脚本
├── start.bat                     # Windows 启动脚本
├── .env.example                  # 后端环境变量示例
├── .env.frontend.example         # 前端环境变量示例
└── model/                        # 语音模型目录（需自行放置，不纳入版本控制）
    ├── SenseVoiceSmall/
    └── speech_fsmn_vad_zh-cn-16k-common-pytorch/
```

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3, Vue Router 4, Vite, Tailwind CSS, Axios, TipTap, Marked |
| 后端 | Python, Flask, Flask-CORS |
| 语音识别 | FunASR (SenseVoiceSmall) |
| 大语言模型 | DeepSeek API (via LangChain / OpenAI SDK) |

## 工作流程

1. **上传音频** — 用户上传 MP3/WAV/M4A/FLAC/WMA 音频文件
2. **语音转写** — 使用 FunASR SenseVoice 模型将音频转为文字
3. **AI 校对** — 将转写文本分块，并发调用 DeepSeek 进行错别字修正与分段
4. **信息填写** — 用户填写会议时间、参会人、记录人、会议类型等
5. **要点提取** — 根据会议类型，分块并发提取关键要点
6. **纪要生成** — 将要点按模板生成结构化 Markdown 会议纪要
7. **AI 辅助编辑** — 在结果页面支持改写、总结、翻译等 AI 操作

## 环境要求

- Python 3.8+
- Node.js 16+
- CUDA GPU（语音识别模型需要）
- DeepSeek API Key

## 快速开始

### 1. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入你的 DeepSeek API Key：

```
DEEPSEEK_API_KEY=sk-your-actual-api-key
```

### 2. 准备语音模型

将以下两个模型放置到 `model/` 目录下：

- `model/SenseVoiceSmall/` — SenseVoice 语音识别模型
- `model/speech_fsmn_vad_zh-cn-16k-common-pytorch/` — VAD 模型

### 3. 安装后端依赖

```bash
pip install flask flask-cors python-dotenv funasr langchain-openai langchain
```

### 4. 安装前端依赖

```bash
npm install
```

### 5. 配置前端环境变量（AI 辅助编辑功能）

```bash
cp .env.frontend.example .env.local
```

编辑 `.env.local`，填入你的 DeepSeek API Key：

```
VITE_DEEPSEEK_API_KEY=sk-your-actual-api-key
```

### 6. 启动服务

**后端：**

```bash
python main.py
```

后端默认运行在 `http://localhost:5000`。

**前端：**

```bash
npm run dev
```

前端默认运行在 `http://localhost:3000`，通过 Vite 代理将 `/api` 请求转发到后端。

或使用启动脚本（自动安装依赖并启动前端）：

```bash
# Linux/macOS
bash start.sh

# Windows
start.bat
```

## 支持的会议类型

| 类型 | 说明 |
|------|------|
| 项目进度 | 项目任务进展、计划分配、风险管理 |
| 问题讨论 | 问题描述、根因分析、解决方案、行动计划 |
| 学习讲座 | 知识要点、问答环节、学习资源 |
| 自定义 | 上传自定义 Markdown 模板，自由生成纪要 |

## 前端构建

```bash
npm run build
```

构建产物输出到 `dist/` 目录。

## 许可证

本项目仅供学习交流使用。
