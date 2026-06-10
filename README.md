# Agenta - 智能会议纪要生成系统

上传会议录音，自动完成语音转写、AI 校对、要点提取，生成结构化会议纪要，并提供 AI 辅助编辑能力。基于 Vue 3 + Flask + FunASR + DeepSeek LLM。

## 快速开始

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY=sk-your-key

# 2. 准备语音模型 → model/ 目录
#    model/SenseVoiceSmall/
#    model/speech_fsmn_vad_zh-cn-16k-common-pytorch/

# 3. 安装依赖
pip install flask flask-cors python-dotenv funasr langchain-openai langchain openai
npm install

# 4. 启动
python main.py          # 后端 :5000
npm run dev             # 前端 :3000
```

需要 Python 3.8+、Node.js 16+、CUDA GPU、DeepSeek API Key。

## 系统架构

```
  上传音频 → 语音转写(FunASR) → AI并发校对 → 填写会议信息
                                              ↓
              AI辅助编辑 ← 纪要编辑器 ← 模板填充生成纪要 ← AI并发提取要点
                  ↓
        改写 / 总结 / 翻译 / 自定义指令
```

前端 Vue 3 通过 Vite 代理 `/api` 访问 Flask 后端；后端通过 subprocess 调用转写和纪要生成脚本，通过 `/api/ai_proxy` 代理 DeepSeek LLM 调用（API Key 不暴露到前端）。每个用户会话分配独立 UUID 工作目录，支持多用户并发。

## 核心特性

- **自动化流水线** — 音频上传到纪要生成全流程自动，支持项目进度、问题讨论、学习讲座、自定义模板四种会议类型
- **长文本并发处理** — 按标点句切分（1250 字/块），asyncio + ThreadPoolExecutor 并发调用 LLM，延迟从线性降到常数级
- **AI 辅助编辑** — TipTap 编辑器集成选区感知，支持改写、总结、翻译等操作，聊天式交互 + 一键替换
- **会话隔离与安全** — UUID 目录隔离、API Key 服务端代理、路径遍历防护、XSS 净化（DOMPurify）、CORS 白名单

## 技术栈

Vue 3 / Vite / Tailwind CSS / TipTap / Flask / FunASR (SenseVoiceSmall + VAD) / LangChain / DeepSeek LLM / asyncio

## 项目结构

```
├── main.py                    # Flask 后端：API 路由、会话管理、AI 代理
├── combined_transcription.py  # 语音转写 + 并发 AI 校对
├── summary.py                 # 并发要点提取 + 模板填充纪要生成
├── SenseVoiceSmall.py         # SenseVoice 独立调用脚本
├── custom.md                  # 自定义模板的 LLM 生成指令
├── prompt_tra.txt             # 转写校对 Prompt
├── ex_prompt_*.txt            # 各类型要点提取 Prompt
├── template_*.md              # 各类型纪要 Markdown 模板
├── src/
│   ├── App.vue                # 根组件（侧边栏 + 步骤导航）
│   ├── main.js                # 路由 + Axios 全局配置
│   └── views/
│       ├── UploadPage.vue     # 音频上传（拖拽 + 进度条）
│       ├── TranscriptionPage.vue  # 转写轮询 + 结果展示
│       ├── TemplatesPage.vue  # 会议信息表单 + 模板选择
│       └── ResultPage.vue     # TipTap 编辑器 + AI 辅助编辑
├── model/                     # 语音模型（gitignore）
└── .env                       # 环境变量（gitignore）
```

## License

MIT
