<template>
    <div class="ai-editor-layout">
        <!-- 编辑器区：两个编辑器上下排列 -->
        <div class="editor-panel">
            <div class="editors-double">
                <!-- 转写编辑器块，支持折叠/展开 -->
                <div class="editor-block" :class="{ 'transcribe-collapsed': transcribeCollapsed }">
                    <div class="editor-label transcribe-label" @click="onTranscribeLabelClick"
                        style="cursor:pointer;user-select:none;">
                        <span :class="['triangle', transcribeCollapsed ? '' : 'expanded']">&#9654;</span>
                        转写
                    </div>
                    <transition name="fade">
                        <div v-show="!transcribeCollapsed" class="editor-content-fixed">
                            <editor-content :editor="transcribeEditor" />
                        </div>
                    </transition>
                </div>
                <div class="hint">💡 请选择需要优化的文本</div>
                <!-- 会议纪要 -->
                <div class="editor-block" :class="{ 'main-expanded': transcribeCollapsed }">
                    <div style="display: flex; align-items: center; justify-content: space-between; padding: 8px 0;">
                        <div class="editor-label" style="font-weight: bold;">会议纪要</div>
                        <!-- 按钮组 -->
                        <div class="note-actions" style="display: flex; gap: 8px;">
                            <button class="preview-toggle-btn" @click="showMarkdownPreview = !showMarkdownPreview"
                            :disabled="isLoadingSummary"
                                style="padding: 4px 10px; font-size: 14px; background-color: #95C11F; color: white; border: none; border-radius: 4px; cursor: pointer;">
                                <i :class="showMarkdownPreview ? 'fa fa-pencil' : 'fa fa-eye'"
                                    style="margin-right: 4px;"></i>
                                {{ showMarkdownPreview ? '编辑' : '预览' }}
                            </button>
                        </div>
                    </div>
                    <div class="editor-content-fixed">
                        <div v-if="isLoadingSummary" class="loading-container">
                            <div class="loading-animation">
                                <div class="pulse-circle"></div>
                                <div class="pulse-circle"></div>
                                <div class="pulse-circle"></div>
                            </div>
                            <p class="loading-text">正在等待会议纪要生成...</p>
                            <p class="loading-subtext">将持续检查文件状态</p>
                        </div>
                        <template v-else>
                            <div v-if="showMarkdownPreview" class="markdown-preview" v-html="markdownHtml"></div>
                            <editor-content v-else :editor="editor" />
                        </template>
                    </div>
                </div>
            </div>
            <div class="button-group" style="margin-top: 12px;">
                <button @click="runAiCommand('rephrase')" :disabled="isDisabled">改写</button>
                <button @click="runAiCommand('summarize')" :disabled="isDisabled">总结</button>
                <button @click="runAiCommand('simplify')" :disabled="isDisabled">简化</button>
                <button @click="runAiCommand('fixSpelling')" :disabled="isDisabled">纠正拼写</button>
                <button @click="runAiCommand('translateChinese')" :disabled="isDisabled">翻译为中文</button>
                <button @click="runAiCommand('translateEnglish')" :disabled="isDisabled">翻译为英语</button>
            </div>
            <!-- 底部操作按钮 -->
            <div class="flex justify-end gap-4 mt-6">
                <button @click="goBack" class="btn-secondary">
                    返回
                </button>
                <button @click="saveMeetingNote" class="btn-primary">
                    保存
                </button>
            </div>
            <div v-if="state.errorMessage" class="hint error">{{ state.errorMessage }}</div>
        </div>

        <!-- 右侧AI结果 -->
        <div class="ai-result-panel">
            <div class="ai-result-title">AI辅助优化</div>
            <div class="ai-chat-history-scroll">
                <template v-if="chatHistory.length > 0">
                    <div v-for="(item, idx) in chatHistory" :key="idx" class="chat-item">
                        <div class="chat-row single">
                            <div class="chat-user-side">
                                <div class="chat-bubble user">
                                    <div class="chat-user"></div>
                                    <div>{{ item.user }}</div>
                                </div>
                            </div>
                        </div>
                        <div class="chat-row single">
                            <div class="chat-ai-side">
                                <div class="chat-bubble ai">
                                    <div class="chat-ai"></div>
                                    <div>{{ item.ai }}</div>
                                </div>
                                <div class="chat-actions left">
                                    <button @click="replaceSelectionFromHistory(idx)" :disabled="!item.ai">替代</button>
                                </div>
                            </div>
                        </div>
                    </div>
                </template>
                <template v-else>
                    <div class="ai-empty-hint">
                        <div class="ai-empty-icon">
                            <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
                                <circle cx="32" cy="32" r="32" fill="#f0f7f0" />
                                <path d="M20 44v-2a8 8 0 0 1 8-8h8a8 8 0 0 1 8 8v2" stroke="#6da34d" stroke-width="2"
                                    stroke-linecap="round" />
                                <circle cx="24" cy="28" r="2" fill="#6da34d" />
                                <circle cx="40" cy="28" r="2" fill="#6da34d" />
                                <path d="M28 36c1.5 2 6.5 2 8 0" stroke="#6da34d" stroke-width="2"
                                    stroke-linecap="round" />
                            </svg>
                        </div>
                        <div class="ai-empty-text">
                            说点什么吧！让AI来帮助你理解会议
                        </div>
                    </div>
                </template>
                <div v-if="state.isLoading" class="hint purple-spinner" style="text-align:center;margin:8px 0;">
                    <span class="spinner"></span> AI 正在生成中……
                </div>
            </div>
            <div>
                <div v-if="selectedTextForPrompt" class="selected-bubble">
                    <span>选中内容：</span>
                    <div class="chat-bubble user">{{ selectedTextForPrompt }}</div>
                </div>
                <div class="ai-custom-prompt">
                    <input v-model="customPrompt" type="text" placeholder="请输入你的问题或需求"
                        @keyup.enter="sendCustomPrompt" />
                    <button @click="sendCustomPrompt" :disabled="!customPrompt || state.isLoading">发送</button>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import StarterKit from '@tiptap/starter-kit'
import { Editor, EditorContent } from '@tiptap/vue-3'
import { Plugin } from '@tiptap/pm/state'
import { Decoration, DecorationSet } from '@tiptap/pm/view'
import { defineComponent } from 'vue'
import { useRoute } from 'vue-router'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

marked.setOptions({
    breaks: true,
    gfm: true,
})

export default defineComponent({
    components: {
        EditorContent,
    },

    data() {
        return {
            state: {
                isLoading: false,
                errorMessage: null,
                response: null,
            },
            editor: null,
            transcribeEditor: null,
            openai: null,
            sid: '',
            highlightRange: null,
            customPrompt: '',
            chatHistory: [],
            transcribeCollapsed: true,
            showMarkdownPreview: true,
            isLoadingSummary: true,
            summaryCheckInterval: null,
            meetingData: {
                transcribe: '',
                note: '',
            },
        }
    },

    computed: {
        isDisabled() {
            if (!this.editor) return true
            return this.editor.isEmpty
        },
        selectedTextForPrompt() {
            if (!this.editor || !this.highlightRange) return ''
            return this.editor.state.doc.textBetween(
                this.highlightRange.from,
                this.highlightRange.to
            )
        },
        markdownHtml() {
            if (!this.editor) return ''
            const rawContent = this.editor.getText()

            // 增强版Markdown转换逻辑，重点处理换行
            let markdownText = rawContent
                // 先将所有换行符统一处理
                .replace(/\r\n/g, '\n') // 处理Windows换行
                .replace(/\r/g, '\n')   // 处理Mac老式换行
                // 处理连续空行作为段落分隔
                .replace(/\n{2,}/g, '\n\n')
                // 处理单行换行（转换为<br>）
                .replace(/([^\n])\n([^\n])/g, '$1\n\n$2')
                // 处理代码块
                .replace(/```([\s\S]*?)```/g, (match, code) => {
                    return '```\n' + code.trim() + '\n```'
                })
                // 处理标题
                .replace(/(#{1,6} .+?)(?=\n|$)/g, '$1\n')
                // 处理列表
                .replace(/^(\s*)-\s/gm, '$1- ')
                .replace(/^(\s*)\*\s/gm, '$1* ')
                .replace(/^(\s*)\d+\.\s/gm, '$11. ')
                .trim()

            return DOMPurify.sanitize(marked.parse(markdownText))
        }
    },

    methods: {
        async fetchSummaryMd() {
            try {
                const sidQuery = this.sid ? `?sid=${this.sid}` : ''
                const response = await fetch(`/api/summary.md${sidQuery}`, { credentials: 'include' })
                if (!response.ok) {
                    // 如果文件不存在，抛出错误让catch处理
                    if (response.status === 404) throw new Error('文件不存在')
                    throw new Error('获取summary.md失败')
                }
                let rawText = await response.text()
                const markdownContent = rawText
                    .replace(/\r\n/g, '<br>') // 处理 Windows 换行
                    .replace(/\r/g, '<br>')   // 处理老式 Mac 换行
                    .replace(/\n/g, '<br>')   // 处理 Unix 换行
                this.editor?.commands.setContent(markdownContent)
                this.isLoadingSummary = false // 加载成功，隐藏加载状态
                return true // 表示成功获取
            } catch (error) {
                console.log('当前未获取到summary.md，将继续尝试:', error.message)
                return false // 表示获取失败
            }
        },

        // 新增：定时检查summary.md的方法
        startSummaryCheck() {
            // 立即执行一次检查
            this.fetchSummaryMd().then(success => {
                if (success) {
                    // 如果成功获取，清除定时器
                    if (this.summaryCheckInterval) {
                        clearInterval(this.summaryCheckInterval)
                        this.summaryCheckInterval = null
                    }
                    return
                }

                // 如果第一次失败，设置定时器每5秒检查一次
                this.summaryCheckInterval = setInterval(async () => {
                    const success = await this.fetchSummaryMd()
                    if (success && this.summaryCheckInterval) {
                        clearInterval(this.summaryCheckInterval)
                        this.summaryCheckInterval = null
                    }
                }, 5000) // 5秒间隔
            })
        },

        async fetchCombinedOutput() {
            try {
                const sidQuery = this.sid ? `?sid=${this.sid}` : ''
                const response = await fetch(`/api/combined_output.txt${sidQuery}`, { credentials: 'include' })
                if (!response.ok) {
                    if (response.status === 404) throw new Error('文件不存在')
                    throw new Error('获取转写失败')
                }
                let rawText = await response.text()
                const formattedText = rawText
                    .replace(/\r\n/g, '<br>') // 处理 Windows 换行
                    .replace(/\r/g, '<br>')   // 处理老式 Mac 换行
                    .replace(/\n/g, '<br>')   // 处理 Unix 换行
                this.transcribeEditor?.commands.setContent(formattedText)
                return true
            } catch (error) {
                console.log('当前未获取到转写，将继续尝试:', error.message)
                return false
            }
        },
        onTranscribeLabelClick() {
            this.transcribeCollapsed = !this.transcribeCollapsed
            if (!this.transcribeCollapsed) {
                this.fetchCombinedOutput()
            }
        },

        initOpenAI() {
        },

        selectAllText() {
            if (!this.editor) return
            const { doc } = this.editor.state
            this.highlightRange = { from: 0, to: doc.content.size }
        },

        async runAiCommand(command) {
            if (!this.editor) return
            const { from, to } = this.editor.state.selection
            let selectedText = this.editor.state.doc.textBetween(from, to)
            let highlightFrom = from, highlightTo = to
            if (from === to) {
                selectedText = this.editor.getText().trim()
                highlightFrom = 0
                highlightTo = this.editor.state.doc.content.size
            }
            this.highlightRange = (from !== to || selectedText) ? { from: highlightFrom, to: highlightTo } : null

            const commandMap = {
                keypoints: '提取要点', rephrase: '改写', summarize: '总结', simplify: '简化',
                fixSpelling: '纠正拼写', continueWriting: '续写', emojify: '添加表情',
                deEmojify: '移除表情', translateChinese: '翻译为中文', translateEnglish: '翻译为英语'
            }
            const userQuestion = `请帮我${commandMap[command]}${from !== to ? '（针对选中内容）' : '（针对全文）'}`
            let prompt = ''
            switch (command) {
                case 'rephrase': prompt = `用不同的表达方式重写以下文本：\n\n${selectedText}`; break
                case 'summarize': prompt = `总结以下文本的主要内容：\n\n${selectedText}`; break
                case 'simplify': prompt = `简化以下文本，使其更容易理解：\n\n${selectedText}`; break
                case 'fixSpelling': prompt = `修正以下文本中的拼写和语法错误：\n\n${selectedText}`; break
                case 'translateChinese': prompt = `将以下文本翻译成中文：\n\n${selectedText}`; break
                case 'translateEnglish': prompt = `将以下文本翻译成英语：\n\n${selectedText}`; break
            }
            try {
                this.state.isLoading = true
                this.state.errorMessage = null
                const response = await fetch('/api/ai_proxy', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ command, prompt }),
                    credentials: 'include',
                })
                const data = await response.json()
                if (!response.ok || data.error) {
                    this.state.errorMessage = data.error || 'AI接口返回异常'
                    this.state.isLoading = false
                    return
                }
                const aiResponse = data.response
                this.state.response = aiResponse
                this.chatHistory.push({ user: userQuestion, ai: aiResponse })
            } catch (error) {
                this.state.errorMessage = `AI处理失败: ${error.message}`
            } finally {
                this.state.isLoading = false
            }
        },

        async sendCustomPrompt() {
            if (!this.customPrompt) return
            this.state.isLoading = true
            this.state.errorMessage = null
            const { from, to } = this.editor.state.selection
            let selectedText = this.editor.state.doc.textBetween(from, to)
            let highlightFrom = from, highlightTo = to
            if (from === to) {
                selectedText = this.editor.getText().trim()
            }
            this.highlightRange = (from !== to || selectedText) ? { from: highlightFrom, to: highlightTo } : null
            let prompt = selectedText
                ? `针对以下文本片段，${this.customPrompt}\n\n${selectedText}`
                : this.customPrompt

            try {
                const response = await fetch('/api/ai_proxy', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ command: 'custom', prompt }),
                    credentials: 'include',
                })
                const data = await response.json()
                if (!response.ok || data.error) {
                    this.state.errorMessage = data.error || 'AI接口返回异常'
                    this.state.isLoading = false
                    return
                }
                const aiResponse = data.response
                this.state.response = aiResponse
                this.chatHistory.push({
                    user: this.customPrompt + (selectedText ? `（针对选中内容）` : ''),
                    ai: aiResponse,
                })
                this.customPrompt = ''
            } catch (error) {
                this.state.errorMessage = `AI处理失败: ${error.message}`
            } finally {
                this.state.isLoading = false
            }
        },

        replaceSelectionFromHistory(idx) {
            const historyItem = this.chatHistory[idx]
            if (!this.editor || !this.highlightRange || !historyItem.ai) return
            const { from, to } = this.highlightRange
            historyItem.originalText = this.editor.state.doc.textBetween(from, to)
            this.editor.chain().focus().deleteRange({ from, to }).insertContent(historyItem.ai).run()
            this.state.response = ''
            this.highlightRange = null
            historyItem.replaced = true
        },

        undoReplaceFromHistory(idx) {
            const historyItem = this.chatHistory[idx]
            if (!this.editor || !this.highlightRange || !historyItem.originalText) return
            const { from, to } = this.highlightRange
            this.editor.chain().focus().deleteRange({ from, to }).insertContent(historyItem.originalText).run()
            historyItem.replaced = false
        },

        discardHistory(idx) {
            this.chatHistory.splice(idx, 1)
        },

        async fetchMeetingData() {
        },

        saveMeetingNote() {
            // 获取会议纪要内容（用markdown格式）
            const note = this.editor?.getText() || ''
            // 生成文件名，带时间戳，md后缀
            const filename = `会议纪要_${new Date().toLocaleDateString().replace(/\//g, '-')}_${new Date().toLocaleTimeString().replace(/:/g, '-')}.md`
            // 创建Blob并下载
            const blob = new Blob([note], { type: 'text/markdown;charset=utf-8' })
            if (window.navigator.msSaveOrOpenBlob) {
                window.navigator.msSaveOrOpenBlob(blob, filename)
            } else {
                const link = document.createElement('a')
                link.href = URL.createObjectURL(blob)
                link.download = filename
                document.body.appendChild(link)
                link.click()
                document.body.removeChild(link)
                URL.revokeObjectURL(link.href)
            }
        },

        goBack() {
            if (confirm('确定要返回吗？未保存的更改将会丢失。')) {
                this.$router.push('/templates');
            }
        }
    },

    watch: {
        chatHistory() {
            this.$nextTick(() => {
                const chatScroll = this.$el.querySelector('.ai-chat-history-scroll')
                if (chatScroll) chatScroll.scrollTop = chatScroll.scrollHeight
            })
        }
    },

    mounted() {
        const route = useRoute()
        this.sid = route.query.sid || ''
        this.initOpenAI()
        this.startSummaryCheck()
        this.fetchMeetingData()
        this.editor = new Editor({
            extensions: [
                StarterKit,
                new Plugin({
                    props: {
                        decorations: () => null
                    }
                })
            ],
            content: '',
            parseOptions: {
                preserveWhitespace: true,
            },
            onSelectionUpdate: ({ editor }) => {
                const { from, to } = editor.state.selection
                this.highlightRange = from !== to ? { from, to } : null
            }
        })
        this.transcribeEditor = new Editor({
            extensions: [StarterKit],
            content: '',
        })
        this.editor.registerPlugin(new Plugin({
            props: {
                decorations: (state) => {
                    if (!this.highlightRange) return null
                    const { from, to } = this.highlightRange
                    return DecorationSet.create(state.doc, [
                        Decoration.inline(from, to, { class: 'ai-highlight' })
                    ])
                }
            }
        }))
        this.$nextTick(() => {
            const chatScroll = this.$el.querySelector('.ai-chat-history-scroll')
            if (chatScroll) chatScroll.scrollTop = chatScroll.scrollHeight
        })
    },

    beforeUnmount() {
        this.editor?.destroy()
        this.transcribeEditor?.destroy()
        if (this.summaryCheckInterval) {
            clearInterval(this.summaryCheckInterval)
        }
    },
})
</script>

<style lang="scss">
// 基础变量调整为低饱和色调，提升简洁感
$primary: #6da34d; // 主色调：低饱和绿色
$primary-light: #f8f9fa; // 浅绿背景
$primary-dark: #4a7d36; // 深绿文字
$primary-accent: #8dc075; // 强调色
$gray-light: #f8f9fa; // 浅灰背景
$gray-mid: #e9ecef; // 边框/分割线
$text-primary: #333333; // 主要文字
$text-secondary: #6c757d; // 次要文字
$shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.05); // 轻量阴影
$shadow-md: 0 4px 12px rgba(0, 0, 0, 0.07); // 中等阴影
$radius-sm: 6px;
$radius-md: 10px;
$radius-lg: 14px;
$transition: all 0.25s ease; // 统一过渡动画

.ai-editor-layout {
    display: flex;
    background: $primary-light;
    height: calc(100vh - 4rem);
    width: 100%;
    font-family: "Inter", "PingFang SC", "Microsoft YaHei", Arial, sans-serif;
    min-height: 0;
    overflow: hidden;
    padding: 12px;
    box-sizing: border-box;
}

.editor-panel {
    flex: 2 1 0;
    min-width: 0;
    background: #fff;
    border-radius: $radius-lg;
    box-shadow: $shadow-md;
    padding: 16px;
    margin: 0 8px 0 0;
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 0;
    overflow: hidden;
    box-sizing: border-box;
}

.editors-double {
    display: flex;
    flex-direction: column;
    gap: 12px;
    flex: 1 1 0;
    min-height: 0;
    overflow: hidden;
}

.editor-block {
    flex: 1 1 0;
    display: flex;
    flex-direction: column;
    background: $gray-light;
    border-radius: $radius-md;
    box-shadow: $shadow-sm;
    padding: 12px;
    transition: flex 0.3s, max-height 0.3s, box-shadow 0.2s;
    min-height: 0;
    overflow: hidden;

    &:hover {
        box-shadow: $shadow-md;
    }

    &.transcribe-collapsed {
        flex: 0 0 auto;
        max-height: 36px;
        padding: 0 12px;
        background: transparent;
        box-shadow: none;
        border-radius: $radius-md $radius-md 0 0;
    }

    &.main-expanded {
        flex: 1 1 auto;
    }
}

.editor-label {
    font-weight: 600;
    font-size: 15px;
    color: $primary-dark;
    margin-bottom: 8px;
    letter-spacing: 0.3px;
    display: flex;
    align-items: center;
}

.editor-content-fixed {
    flex: 1 1 0;
    min-height: 0;
    height: 100%;
    width: 100%;
    overflow-y: auto;
    border-radius: $radius-sm;
    border: none;
    background: transparent;
    margin-bottom: 0;
    box-shadow: none;
    position: relative;
    display: flex;
    flex-direction: column;

    >.tiptap-editor,
    >.ProseMirror {
        flex: 1 1 0;
        width: 100%;
        min-height: 0;
        height: 100%;
        box-sizing: border-box;
        background: transparent;
        border: none;
        margin: 0;
        padding: 6px 0;
        overflow-y: auto;
        display: block;
        line-height: 1.5;
        font-size: 14px;
        color: $text-primary;
    }
}

.ProseMirror:focus {
    outline: none !important;
    box-shadow: none !important;
}

// 功能按钮组优化
.button-group {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin: 12px 0 0 0;
    padding-bottom: border-box;

    button {
        background: $primary;
        color: #fff;
        border: none;
        border-radius: $radius-sm;
        padding: 6px 12px;
        font-size: 13px;
        font-weight: 500;
        cursor: pointer;
        transition: $transition;
        box-shadow: $shadow-sm;
        display: inline-flex;
        align-items: center;
        justify-content: center;

        &:hover {
            background: $primary-dark;
            transform: translateY(-1px);
            box-shadow: 0 3px 9px rgba(109, 163, 77, 0.2);
        }

        &:active {
            transform: translateY(0);
        }

        &:disabled {
            background: $gray-mid;
            color: #aaa;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }
    }
}

// 纪要操作按钮
.note-actions {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    /* 减小按钮间距 */
    margin-top: 12px;
    /* 减小间距 */
    margin-bottom: 0;

    button {
        display: flex;
        align-items: center;
        gap: 4px;
        padding: 7px 16px;
        border-radius: $radius-sm;
        border: none;
        font-size: 13px;
        font-weight: 500;
        background: $primary;
        color: #fff;
        box-shadow: $shadow-sm;
        cursor: pointer;
        transition: $transition;

        i {
            font-size: 14px;
        }

        &:hover {
            background: $primary-dark;
            transform: translateY(-1px);
            box-shadow: 0 3px 9px rgba(109, 163, 77, 0.2);
        }

        &:active {
            transform: translateY(0);
        }

        &:disabled {
            background: $gray-mid;
            color: #aaa;
            cursor: not-allowed;
            box-shadow: none;
            transform: none;
        }
    }
}

// 提示文本样式
.hint {
    margin-bottom: 8px;
    font-size: 13px;
    color: $primary-dark;
    padding: 4px 0;
    line-height: 1.4;

    &.error {
        color: #d93025;
        background: #fff0f0;
        border-radius: $radius-sm;
        padding: 6px 10px;
        margin-top: 6px;
    }

    &.purple-spinner {
        font-weight: 500;
        padding: 8px 0;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 6px;

        .spinner {
            display: inline-block;
            width: 14px;
            height: 14px;
            border: 2px solid rgba(109, 163, 77, 0.3);
            border-radius: 50%;
            border-top-color: $primary;
            animation: spin 1s ease-in-out infinite;
        }
    }
}

@keyframes spin {
    to {
        transform: rotate(360deg);
    }
}

.editor-placeholder {
    color: #999;
    padding: 16px;
    text-align: center;
    position: absolute;
    width: 100%;
    pointer-events: none;
    z-index: 1;
    font-size: 14px;
    background: $gray-light;
    border-radius: $radius-sm;
    box-sizing: border-box;
}

// 右侧AI结果面板
.ai-result-panel {
    flex: 1 1 0;
    min-width: 0;
    height: 100%;
    display: flex;
    flex-direction: column;
    gap: 12px;
    background: #fff;
    border-radius: $radius-lg;
    box-shadow: $shadow-md;
    padding: 16px;
    margin: 0 0 0 8px;
    position: relative;
    min-height: 0;
    overflow: hidden;
    box-sizing: border-box;
}

.ai-result-title {
    font-weight: 600;
    font-size: 16px;
    margin-bottom: 2px;
    color: $primary-dark;
    letter-spacing: 0.3px;
    padding-bottom: 6px;
    border-bottom: 1px solid $gray-mid;
}

.ai-chat-history-scroll {
    flex: 1 1 0;
    min-height: 0;
    max-height: calc(100% - 120px);
    overflow-y: auto;
    padding: 6px 3px;
    margin-bottom: 6px;
    scrollbar-width: thin;
    scrollbar-color: $primary $primary-light;
    background: $gray-light;
    border-radius: $radius-md;
    box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.03);

    &::-webkit-scrollbar {
        width: 5px;
    }

    &::-webkit-scrollbar-thumb {
        background: $primary;
        border-radius: 3px;
    }

    &::-webkit-scrollbar-track {
        background: $primary-light;
        border-radius: 3px;
    }
}

// 聊天记录样式
.chat-item {
    margin-bottom: 10px;
    padding: 0 6px;
}

.chat-row {
    display: flex;
    justify-content: flex-start;
    align-items: flex-end;
    gap: 8px;
}

.chat-user-side {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    max-width: 75%;
    margin-left: auto;
}

.chat-ai-side {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    max-width: 75%;
}

.chat-bubble {
    position: relative;
    padding: 8px 12px;
    border-radius: 14px;
    margin-bottom: 3px;
    max-width: 100%;
    word-break: break-word;
    font-size: 13px;
    line-height: 1.5;
    box-shadow: $shadow-sm;

    &.ai {
        background: #fff;
        color: $text-primary;
        border-bottom-left-radius: 4px;
        border-top-left-radius: 4px;
        margin-left: 3px;
        align-self: flex-start;

        &::before {
            content: "";
            position: absolute;
            left: -5px;
            top: 10px;
            border-width: 5px 7px 5px 0;
            border-style: solid;
            border-color: transparent #fff transparent transparent;
        }
    }

    &.user {
        background: $primary;
        color: #fff;
        border-bottom-right-radius: 4px;
        border-top-right-radius: 4px;
        margin-right: 3px;
        align-self: flex-end;

        &::before {
            content: "";
            position: absolute;
            right: -5px;
            top: 10px;
            border-width: 5px 0 5px 7px;
            border-style: solid;
            border-color: transparent transparent transparent $primary;
        }
    }
}

// 聊天操作按钮
.chat-actions {
    display: flex;
    gap: 5px;
    margin-top: 1px;

    &.left {
        justify-content: flex-start;
        padding-left: 20px;
    }

    button {
        background: $primary-light;
        color: $primary-dark;
        border: none;
        border-radius: 4px;
        padding: 3px 12px;
        font-size: 14px;
        margin-left: -15px;
        cursor: pointer;
        box-shadow: $shadow-sm;
        transition: $transition;

        &:hover {
            background: $primary;
            color: #fff;
        }

        &:disabled {
            background: $gray-mid;
            color: #aaa;
            cursor: not-allowed;
        }
    }
}

// 选中内容气泡
.selected-bubble {
    margin-bottom: 10px;
    font-size: 14px;
    color: $text-secondary;
    display: flex;
    align-items: flex-start;
    gap: 6px;
    flex-wrap: wrap;
    word-break: break-all;
    align-items: center;

    .chat-bubble.user {
        display: inline-block;
        margin-left: 0;
        background: $primary-light;
        padding: 6px 12px;
        border-radius: 10px;
        max-width: 100%;
        word-break: break-all;
        font-size: 14px;
        box-shadow: $shadow-sm;
        color: $primary-dark;
        max-height: 4.5em;
        overflow-y: auto;
        overflow-x: hidden;
        white-space: pre-line;
    }

    .chat-bubble.user::-webkit-scrollbar {
        display: none;
    }

    .chat-bubble.user::before {
        display: none;
    }
}

.ai-custom-prompt {
    display: flex;
    gap: 10px;
    margin-bottom: 4px;

    input {
        flex: 1;
        padding: 8px 12px;
        border-radius: $radius-sm;
        border: 1px solid $primary-light;
        font-size: 14px;
        background: $gray-light;
        box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.05);
        color: $text-primary;
        transition: $transition;

        &:focus {
            outline: none;
            border-color: $primary;
            box-shadow: 0 0 0 2px rgba(109, 163, 77, 0.2);
        }

        &::placeholder {
            color: #999;
        }
    }

    button {
        padding: 0 16px;
        border-radius: $radius-sm;
        background: $primary;
        color: #fff;
        border: none;
        cursor: pointer;
        font-size: 14px;
        font-weight: 500;
        box-shadow: $shadow-sm;
        transition: $transition;

        &:hover {
            background: $primary-dark;
            transform: translateY(-1px);
        }

        &:active {
            transform: translateY(0);
        }

        &:disabled {
            background: $gray-mid;
            color: #aaa;
            cursor: not-allowed;
            box-shadow: none;
            transform: none;
        }
    }
}

// 折叠三角图标
.transcribe-label {
    display: flex;
    align-items: center;
    gap: 6px;
}

.triangle {
    display: inline-block;
    transition: transform 0.2s ease;
    font-size: 14px;
    color: $primary;

    &.expanded {
        transform: rotate(90deg);
    }
}

// 折叠过渡动画
.fade-enter-active,
.fade-leave-active {
    transition: opacity 0.2s ease, transform 0.2s ease;
    transform: translateY(0);
    opacity: 1;
}

.fade-enter-from,
.fade-leave-to {
    opacity: 0;
    transform: translateY(-8px);
}

// 空状态样式
.ai-empty-hint {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 70%;
    color: #b7e28a;
    user-select: none;
    pointer-events: none;

    .ai-empty-icon {
        margin-bottom: 12px;
        opacity: 0.8;
        transform: scale(0.9);
    }

    .ai-empty-text {
        font-size: 14px;
        /* 减小字体 */
        color: $primary;
        font-weight: 500;
        letter-spacing: 0.3px;
        text-align: center;
    }
}

// Markdown预览样式优化
.markdown-preview {
    margin-top: 0;
    padding: 10px 0;
    background: transparent;
    border-radius: 0;
    border: none;
    font-size: 16px;
    color: $text-primary;
    height: 100%;
    max-height: none;
    overflow: auto;
    width: 100%;
    box-shadow: none;
    line-height: 1.7;

    /* Markdown基础样式优化 */
    h1,
    h2,
    h3,
    h4,
    h5,
    h6 {
        font-weight: 600;
        margin: 1em 0 0.5em 0;
        /* 减小标题间距 */
        color: $primary-dark;
        line-height: 1.3;
    }

    h1 {
        font-size: 1.6em;
        border-bottom: 2px solid $primary-light;
        padding-bottom: 0.2em;
        margin-top: 0.4em;
    }

    h2 {
        font-size: 1.4em;
        border-bottom: 1px solid $primary-light;
        padding-bottom: 0.1em;
    }

    h3 {
        font-size: 1.2em;
        color: $primary;
    }

    h4,
    h5,
    h6 {
        font-size: 1em;
    }

    p {
        margin: 0.6em 0;
        line-height: 1.6;
    }

    ul,
    ol {
        margin: 0.6em 0;
        padding-left: 1.5em;
    }

    li {
        margin: 0.3em 0;
        line-height: 1.5;
    }

    // 嵌套列表样式
    ul ul,
    ol ol,
    ul ol,
    ol ul {
        margin-left: 0.4em;
        padding-left: 0.8em;
    }

    table {
        border-collapse: collapse;
        margin: 1em 0;
        width: 100%;
        font-size: 13px;
        background: #fff;
        border-radius: $radius-sm;
        overflow: hidden;
    }

    th,
    td {
        border: 1px solid $gray-mid;
        padding: 6px 10px;
        text-align: left;
    }

    th {
        background: $primary-light;
        color: $primary-dark;
        font-weight: 600;
    }

    code {
        background: $primary-light;
        border-radius: 3px;
        padding: 0.1em 0.3em;
        font-size: 12px;
        color: $primary-dark;
        font-family: 'Fira Mono', 'Consolas', 'Menlo', monospace;
    }

    pre code {
        display: block;
        padding: 10px;
        background: $gray-light;
        border-radius: $radius-sm;
        font-size: 12px;
        overflow-x: auto;
        border: 1px solid $gray-mid;
    }

    blockquote {
        border-left: 3px solid $primary;
        background: $primary-light;
        margin: 0.8em 0;
        padding: 0.5em 0.8em;
        color: $text-secondary;
        border-radius: 0 $radius-sm $radius-sm 0;
    }

    strong {
        font-weight: 600;
        color: $primary-dark;
    }

    em {
        font-style: italic;
        color: $primary-dark;
    }

    hr {
        border: none;
        border-top: 1px solid $gray-mid;
        margin: 1.2em 0;
    }
}

// 选中高亮样式
.ai-highlight {
    background: rgba(141, 192, 117, 0.2) !important;
    border-radius: 2px;
    padding: 0 2px;
}

.summary-loading {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    background: rgba(255, 255, 255, 0.9);
    padding: 12px 20px;
    border-radius: 6px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    z-index: 100;
    display: flex;
    align-items: center;
    gap: 8px;
    color: #6da34d;
    font-weight: 500;
    font-size: 13px;

    .spinner {
        display: inline-block;
        width: 16px;
        height: 16px;
        border: 2px solid rgba(109, 163, 77, 0.3);
        border-radius: 50%;
        border-top-color: #6da34d;
        animation: spin 1s ease-in-out infinite;
    }
}

.loading-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    width: 100%;
    background-color: $gray-light;
    border-radius: $radius-sm;
    padding: 2rem;
    box-sizing: border-box;
}

.loading-animation {
    display: flex;
    gap: 0.8rem;
    margin-bottom: 1.5rem;
}

.pulse-circle {
    width: 1.2rem;
    height: 1.2rem;
    border-radius: 50%;
    background-color: $primary;
    animation: pulse 1.4s infinite ease-in-out both;

    &:nth-child(1) {
        animation-delay: -0.32s;
    }

    &:nth-child(2) {
        animation-delay: -0.16s;
    }
}

@keyframes pulse {

    0%,
    80%,
    100% {
        transform: scale(0);
        opacity: 0.6;
    }

    40% {
        transform: scale(1);
        opacity: 1;
    }
}

.loading-text {
    font-size: 15px;
    color: $primary-dark;
    margin: 0 0 0.5rem 0;
    font-weight: 500;
}

.loading-subtext {
    font-size: 13px;
    color: $text-secondary;
    margin: 0;
}

// 确保编辑器在加载时不显示
.editor-content-fixed {

    >.tiptap-editor,
    >.ProseMirror {
        display: none; // 默认隐藏编辑器内容
    }

    // 当加载完成后显示编辑器
    &:not(:has(.loading-container)) {

        >.tiptap-editor,
        >.ProseMirror {
            display: block;
        }
    }
}
</style>