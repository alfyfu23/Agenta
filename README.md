# Agenta - 智能会议纪要生成系统

基于 Vue 3 + Flask + FunASR + DeepSeek LLM 的端到端智能会议纪要系统。上传会议录音，自动完成语音转写、AI 校对、要点提取与结构化纪要生成，并提供 AI 辅助编辑能力。

## 项目亮点

- **端到端自动化流水线**：音频上传 → 语音转写（FunASR） → AI 文本校对 → 要点提取 → 模板填充生成纪要，全流程无需人工干预
- **长文本并发处理**：自定义按句切分算法将长文本分块，通过 `asyncio + ThreadPoolExecutor` 并发调用 LLM，显著降低处理延迟
- **会话隔离架构**：基于 UUID 的会话目录隔离机制，支持多用户并发使用，避免数据串扰
- **AI 辅助富文本编辑器**：集成 TipTap 编辑器，支持选区感知的 AI 改写、总结、翻译等操作，实时预览 Markdown 渲染效果
- **安全设计**：API Key 服务端代理（不暴露前端）、文件上传路径遍历防护、XSS 净化（DOMPurify）、CORS 白名单、会话鉴权

## 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                     Vue 3 Frontend                       │
│  ┌──────────┐ ┌──────────────┐ ┌────────┐ ┌───────────┐ │
│  │ Upload   │→│ Transcription│→│Template│→│  Result   │ │
│  │ Page     │ │ Page (Poll)  │ │  Page  │ │ Page+AI   │ │
│  └──────────┘ └──────────────┘ └────────┘ └───────────┘ │
│       │              │              │            │        │
│       └──────────────┴──────────────┴────────────┘        │
│                     Vite Proxy (/api)                     │
└─────────────────────────┬───────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────┐
│                    Flask Backend                          │
│  ┌─────────┐ ┌──────────────┐ ┌──────────┐ ┌─────────┐  │
│  │ Upload  │ │ Transcribe   │ │ Summary  │ │AI Proxy │  │
│  │ +Validate│ │ Subprocess   │ │Subprocess│ │(LLM)   │  │
│  └────┬────┘ └──────┬───────┘ └────┬─────┘ └────┬────┘  │
│       │             │              │             │        │
│  ┌────▼─────────────▼──────────────▼─────────────▼────┐  │
│  │         Session-Isolated Working Dir               │  │
│  │              uploads/<session_id>/                  │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          │
           ┌──────────────┼──────────────┐
           ▼              ▼              ▼
    ┌────────────┐ ┌────────────┐ ┌────────────┐
    │  FunASR    │ │  DeepSeek  │ │ DeepSeek   │
    │ SenseVoice │ │  校对/提取  │ │ AI编辑代理  │
    │ (GPU/VAD)  │ │ (并发分块)  │ │ (流式响应)  │
    └────────────┘ └────────────┘ └────────────┘
```

## 技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| 前端框架 | Vue 3 + Vue Router 4 | SPA 应用，Composition API |
| 构建工具 | Vite 4 | 开发服务器 + API 代理 |
| UI / 样式 | Tailwind CSS | 原子化 CSS |
| 富文本编辑 | TipTap (ProseMirror) | 会议纪要编辑器 |
| Markdown 渲染 | Marked + DOMPurify | 纪要预览 + XSS 防护 |
| HTTP 客户端 | Axios | 带进度的文件上传 |
| 后端框架 | Flask + Flask-CORS | RESTful API |
| 会话管理 | Flask Session + UUID | 多用户会话隔离 |
| 文件安全 | Werkzeug secure_filename | 路径遍历防护 |
| 语音识别 | FunASR (SenseVoiceSmall + VAD) | 音频转文字 |
| LLM 调用 | LangChain + OpenAI SDK | 文本校对、要点提取、纪要生成 |
| 异步并发 | asyncio + ThreadPoolExecutor | 分块并发调用 LLM |

## 核心模块说明

### 后端（Python / Flask）

| 文件 | 职责 |
|------|------|
| `main.py` | Flask 主入口，REST API，会话管理，文件上传校验，AI 代理 |
| `combined_transcription.py` | SenseVoice 语音转写 + 并发分块 AI 校对 |
| `summary.py` | 并发要点提取 + PromptTemplate 模板填充生成纪要 |
| `SenseVoiceSmall.py` | SenseVoice 独立调用脚本 |
| `transcription.py` | AI 文本校对独立调用脚本 |

### 前端（Vue 3）

| 文件 | 职责 |
|------|------|
| `UploadPage.vue` | 拖拽/选择上传，格式校验，上传进度，会议命名 |
| `TranscriptionPage.vue` | 轮询转写进度，动画进度条，转写结果展示与导出 |
| `TemplatesPage.vue` | 会议信息表单，会议类型选择，自定义模板上传 |
| `ResultPage.vue` | TipTap 富文本编辑器，Markdown 预览，AI 辅助编辑（改写/总结/翻译），聊天式交互 |

### Prompt 工程

| 文件 | 用途 |
|------|------|
| `prompt_tra.txt` | 转写文本校对 Prompt（纠错 + 分段） |
| `ex_prompt_*.txt` | 按会议类型分别设计的关键要点提取 Prompt |
| `template_*.md` | 按会议类型分别设计的结构化纪要 Markdown 模板 |

## 工作流程

```
用户上传音频
    │
    ▼
┌─────────────────────────────────┐
│ 1. FunASR SenseVoice 语音转写   │
│    - VAD 人声检测分段            │
│    - 自动语言识别                │
│    - 转写结果保存                │
└──────────────┬──────────────────┘
               ▼
┌─────────────────────────────────┐
│ 2. AI 并发校对（DeepSeek）       │
│    - 按标点句切分（1250字/块）    │
│    - asyncio 并发请求            │
│    - 纠错 + 重新分段             │
└──────────────┬──────────────────┘
               ▼
┌─────────────────────────────────┐
│ 3. 用户填写会议信息              │
│    - 会议时间、参会人、记录人     │
│    - 选择会议类型                │
│    - 个性化要求（可选）           │
│    - 自定义模板上传（可选）       │
└──────────────┬──────────────────┘
               ▼
┌─────────────────────────────────┐
│ 4. AI 并发要点提取               │
│    - 按会议类型加载专用 Prompt    │
│    - 分块并发提取关键要点         │
└──────────────┬──────────────────┘
               ▼
┌─────────────────────────────────┐
│ 5. 模板填充生成纪要              │
│    - LangChain PromptTemplate   │
│    - 要点 + 会议信息 → Markdown  │
└──────────────┬──────────────────┘
               ▼
┌─────────────────────────────────┐
│ 6. AI 辅助编辑                   │
│    - TipTap 富文本编辑           │
│    - 选区感知：改写/总结/翻译     │
│    - 聊天式 AI 交互面板          │
│    - 一键替换原文                │
└─────────────────────────────────┘
```

## 关键技术实现

### 长文本并发处理

自定义按句切分算法，以标点符号（。！？.?!）为切分边界，每块约 1250 字，通过 `asyncio.gather` + `ThreadPoolExecutor` 并发调用 LLM，将长音频校对和要点提取的延迟从线性降低到常数级：

```python
async def process_transcription(session_dir):
    chunks = chunk_text_with_overlap(user_input)  # 按句切分
    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor() as executor:
        tasks = [process_chunk(executor, loop, llm, prompt, chunk, i, total)
                 for i, chunk in enumerate(chunks)]
        results = await asyncio.gather(*tasks)    # 并发执行
```

### 会话隔离设计

每个用户会话分配独立 UUID 工作目录，所有中间文件（转写结果、会议信息、纪要）均在会话目录内读写，前端通过 URL 参数 `sid` 显式传递会话标识，避免 Cookie 时序问题：

```python
sessions = {}

def _get_session_id():
    sid = request.args.get('sid') or request.headers.get('X-Session-Id')
    if not sid or sid not in sessions:
        sid = str(uuid.uuid4())
        sessions[sid] = {'dir': os.path.join(UPLOAD_FOLDER, sid)}
        os.makedirs(sessions[sid]['dir'], exist_ok=True)
    return sid
```

### AI 辅助编辑

集成 TipTap 编辑器，通过 `onSelectionUpdate` 回调实时追踪用户选区，结合高亮装饰器（ProseMirror Decoration）可视化选中范围。AI 操作通过后端代理调用，API Key 不暴露到前端：

```
用户选中文本 → Tiptap onSelectionUpdate → 记录选区范围
                                          ↓
点击 AI 按钮 → POST /api/ai_proxy → 后端调用 DeepSeek → 返回结果 → 聊天记录展示 → 一键替换
```

## 支持的会议类型

| 类型 | Prompt 策略 | 纪要模板 |
|------|------------|---------|
| 项目进度 | 提取任务进展、计划分配、风险 | 任务清单 + 时间线 + 责任人 |
| 问题讨论 | 提取问题描述、根因、解决方案 | 问题描述 + 根因分析 + 行动计划 |
| 学习讲座 | 提取知识要点、问答环节 | 主题摘要 + 要点列表 + Q&A |
| 自定义 | 使用用户上传的模板 | 用户自定义 Markdown 模板 |

## 项目结构

```
├── main.py                       # Flask 后端：API 路由、会话管理、文件校验、AI 代理
├── combined_transcription.py     # 语音转写 + 并发 AI 校对流水线
├── transcription.py              # AI 文本校对（独立脚本）
├── SenseVoiceSmall.py            # SenseVoice 语音转写（独立脚本）
├── summary.py                    # 并发要点提取 + 模板填充纪要生成
├── prompt_tra.txt                # 转写校对 Prompt
├── ex_prompt_*.txt               # 各类型要点提取 Prompt
├── template_*.md                 # 各类型纪要 Markdown 模板
├── src/                          # Vue 3 前端
│   ├── App.vue                   # 根组件（侧边栏 + 步骤条导航）
│   ├── main.js                   # 路由配置 + Axios 全局配置
│   ├── style.css                 # Tailwind 全局样式 + 自定义组件样式
│   └── views/
│       ├── UploadPage.vue        # 音频上传（拖拽 + 进度条）
│       ├── TranscriptionPage.vue # 转写轮询 + 结果展示
│       ├── TemplatesPage.vue     # 会议信息表单 + 模板选择
│       └── ResultPage.vue        # TipTap 编辑器 + AI 辅助编辑
├── vite.config.js                # Vite 开发服务器 + API 代理
├── tailwind.config.js            # Tailwind CSS 主题配置
├── .env.example                  # 后端环境变量
└── model/                        # 语音模型（不纳入版本控制）
    ├── SenseVoiceSmall/
    └── speech_fsmn_vad_zh-cn-16k-common-pytorch/
```

## 环境要求

- Python 3.8+
- Node.js 16+
- CUDA GPU（语音识别模型推理）
- DeepSeek API Key

## 快速开始

### 1. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，填入 DeepSeek API Key：

```
DEEPSEEK_API_KEY=sk-your-actual-api-key
```

### 2. 准备语音模型

将以下模型放置到 `model/` 目录：

- `model/SenseVoiceSmall/` — SenseVoice 语音识别模型
- `model/speech_fsmn_vad_zh-cn-16k-common-pytorch/` — VAD 人声检测模型

### 3. 安装依赖

```bash
# 后端
pip install flask flask-cors python-dotenv funasr langchain-openai langchain openai

# 前端
npm install
```

### 4. 启动服务

```bash
# 后端（http://localhost:5000）
python main.py

# 前端（http://localhost:3000，自动代理 /api → 后端）
npm run dev
```

或使用启动脚本：

```bash
bash start.sh    # Linux/macOS
start.bat        # Windows
```

### 5. 前端构建

```bash
npm run build
```

构建产物输出到 `dist/` 目录。

## 许可证

MIT License
