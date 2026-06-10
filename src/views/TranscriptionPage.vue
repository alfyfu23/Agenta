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
    <div class="border-2 border-dashed border-border rounded-xl p-6 mb-8 min-h-[300px]">
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
        const progressText = ref('转写结果')
        const progressBarWidth = ref(0)
        const transcription = ref('')
        const isCompleted = ref(false)

        let progressInterval = null
        let checkInterval = null
        const sid = ref('')

        // 模拟进度条动画
        const startProgressAnimation = () => {
            let progress = -2
            progressInterval = setInterval(() => {
                progress += 1
                if (progress > 95) progress = 95 // 保留最后5%等待完成
                if (progress <= 0) {
                    progressBarWidth.value = 0
                    progressText.value = '转写结果'
                } else {
                    progressBarWidth.value = progress
                    progressText.value = `正在转写中...${progress}%`
                }
            }, 750)
        }

        // 检查转写结果
        const checkTranscription = async () => {
            try {
                const response = await axios.get(`/api/check_transcription?sid=${sid.value}`)
                const data = response.data

                if (data.completed) {
                    // 清除进度动画
                    if (progressInterval) {
                        clearInterval(progressInterval)
                    }
                    if (checkInterval) {
                        clearInterval(checkInterval)
                    }

                    // 更新进度为100%
                    progressBarWidth.value = 100
                    progressText.value = '转写完成'
                    transcription.value = data.transcription
                    isCompleted.value = true
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
            }, 0)

            alert('转写结果已成功保存')
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

        // 组件挂载时启动进度检查
        onMounted(() => {
            sid.value = route.query.sid || ''
            startProgressAnimation()

            // 每秒检查一次转写结果
            checkInterval = setInterval(checkTranscription, 1000)
        })

        // 组件卸载时清理定时器
        onUnmounted(() => {
            if (progressInterval) {
                clearInterval(progressInterval)
            }
            if (checkInterval) {
                clearInterval(checkInterval)
            }
        })

        return {
            progressText,
            progressBarWidth,
            transcription,
            isCompleted,
            exportTranscription,
            goBack,
            goNext
        }
    }
}
</script>