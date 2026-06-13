<template>
  <div class="p-6 md:p-8">
    <!-- 进度提示和进度条 -->
    <div class="mb-6">
      <div class="flex justify-between items-center mb-2">
        <p class="text-neutral">
          {{ progressText }}
        </p>
      </div>
      <div class="h-2 bg-gray-200 rounded-full overflow-hidden">
        <div
          class="h-full bg-primary rounded-full transition-all duration-500"
          :style="{ width: progressBarWidth + '%' }"
        />
      </div>
    </div>

    <!-- 对话内容区域 -->
    <div
      v-if="errorMessage"
      class="border-2 border-red-300 rounded-xl p-6 mb-8 bg-red-50"
    >
      <p class="text-red-600 font-medium">
        转写失败
      </p>
      <p class="text-red-500 text-sm mt-2">
        {{ errorMessage }}
      </p>
    </div>
    <div
      v-else
      class="border-2 border-dashed border-border rounded-xl p-6 mb-8 min-h-[300px]"
    >
      <div class="mb-6">
        <p
          class="text-gray-600 text-lg"
          style="white-space: pre-wrap;"
        >
          {{ transcription }}
        </p>
      </div>
    </div>

    <!-- 底部操作按钮 -->
    <div class="flex justify-between items-center">
      <button
        class="btn-secondary"
        @click="exportTranscription"
      >
        直接保存
      </button>
      <div class="flex gap-3">
        <button
          class="btn-secondary"
          @click="goBack"
        >
          返回
        </button>
        <button
          class="btn-primary"
          @click="goNext"
        >
          下一步
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import axios from 'axios'

export default {
    name: 'TranscriptionPage',
    setup() {
        const router = useRouter()
        const route = useRoute()

        // 响应式数据
        const progressText = ref('准备转写...')
        const progressBarWidth = ref(0)
        const transcription = ref('')
        const errorMessage = ref('')

        let progressInterval = null
        let checkInterval = null
        let pollCount = 0
        let isDone = false
        const sid = ref('')

        // 模拟进度条动画
        const startProgressAnimation = () => {
            let progress = 0
            progressText.value = '正在转写中...'
            progressInterval = setInterval(() => {
                progress += 1
                if (progress > 95) progress = 95
                progressBarWidth.value = progress
                progressText.value = `正在转写中...${progress}%`
            }, 750)
        }

        // 检查转写结果
        const checkTranscription = async () => {
            try {
                const response = await axios.get(`/api/check_transcription?sid=${sid.value}`)
                const data = response.data

                if (data.completed) {
                    if (data.error) {
                        if (progressInterval) clearInterval(progressInterval)
                        if (checkInterval) clearInterval(checkInterval)
                        progressBarWidth.value = 0
                        progressText.value = '转写失败'
                        errorMessage.value = data.error
                        return
                    }

                    if (progressInterval) clearInterval(progressInterval)
                    if (checkInterval) clearInterval(checkInterval)

                    progressBarWidth.value = 100
                    progressText.value = '转写完成'
                    transcription.value = data.transcription
                    isDone = true
                }
            } catch (error) {
                console.error('检查转写结果出错:', error)
            }
        }

        // 导出转写结果
        const exportTranscription = () => {
            if (!transcription.value.trim()) {
                alert('没有可保存的转写内容')
                return
            }

            // 创建文件名（使用当前日期和时间）
            const now = new Date()
            const fileName = `转写结果_${now.getFullYear()}${(now.getMonth() + 1).toString().padStart(2, '0')}${now.getDate().toString().padStart(2, '0')}_${now.getHours().toString().padStart(2, '0')}${now.getMinutes().toString().padStart(2, '0')}.txt`

            // 创建Blob对象
            const blob = new Blob([transcription.value], { type: 'text/plain;charset=utf-8' })

            // 创建下载链接
            const url = URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = url
            a.download = fileName

            // 触发下载
            document.body.appendChild(a)
            a.click()

            // 清理
            setTimeout(() => {
                document.body.removeChild(a)
                URL.revokeObjectURL(url)
            }, 100)
        }

        // 返回上一页
        const goBack = () => {
            router.push('/')
        }

        // 下一步
        const goNext = () => {
            const sidQuery = sid.value ? `?sid=${sid.value}` : ''
            router.push(`/templates${sidQuery}`)
        }

        const scheduleNextPoll = () => {
            pollCount++
            const delay = pollCount < 10 ? 1000 : pollCount < 30 ? 2000 : 5000
            checkInterval = setTimeout(async () => {
                await checkTranscription()
                if (!isDone && !errorMessage.value) {
                    scheduleNextPoll()
                }
            }, delay)
        }

        onMounted(() => {
            sid.value = route.query.sid || ''
            startProgressAnimation()
            scheduleNextPoll()
        })

        onUnmounted(() => {
            if (progressInterval) clearInterval(progressInterval)
            if (checkInterval) clearTimeout(checkInterval)
        })

        return {
            progressText,
            progressBarWidth,
            transcription,
            errorMessage,
            exportTranscription,
            goBack,
            goNext
        }
    }
}
</script>