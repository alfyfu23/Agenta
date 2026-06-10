<template>
    <div class="p-6 md:p-8">
        <!-- 标题区域 -->
        <div class="mb-8 text-center">
            <h2 class="text-2xl font-bold">会议基本信息</h2>
        </div>

        <!-- 表单区域 -->
        <div class="max-w-2xl mx-auto space-y-6">
            <!-- 会议时间模块 -->
            <div>
                <label class="block text-neutral mb-2">会议时间</label>
                <div class="relative">
                    <input v-model="meetingTime" type="datetime-local" class="form-input-style">
                    <div class="absolute left-3 top-1/2 -translate-y-1/2 text-neutral">
                        <i class="fa fa-calendar"></i>
                    </div>
                </div>
            </div>

            <!-- 参会人员模块 -->
            <div>
                <label class="block text-neutral mb-2">参会人员</label>
                <div class="relative">
                    <input v-model="participants" type="text" placeholder="输入参会人员姓名" class="form-input-style">
                    <div class="absolute left-3 top-1/2 -translate-y-1/2 text-neutral">
                        <i class="fa fa-user"></i>
                    </div>
                </div>
            </div>

            <!-- 记录人模块 -->
            <div>
                <label class="block text-neutral mb-2">记录人</label>
                <div class="relative">
                    <input v-model="recorder" type="text" placeholder="输入记录人" class="form-input-style">
                    <div class="absolute left-3 top-1/2 -translate-y-1/2 text-neutral">
                        <i class="fa fa-pencil"></i>
                    </div>
                </div>
            </div>

            <!-- 会议类型模块 -->
            <div>
                <label class="block text-neutral mb-2">会议类型</label>
                <div class="relative">
                    <!-- 自定义下拉选择框 -->
                    <div @click="toggleDropdown" class="form-input-style cursor-pointer">
                        <span :class="selectedMeetingType ? 'text-gray-800' : 'text-placeholder'">
                            {{ selectedMeetingTypeText }}
                        </span>
                    </div>
                    <div class="absolute left-3 top-1/2 -translate-y-1/2 text-neutral">
                        <i class="fa fa-list-ul"></i>
                    </div>
                    <div @click="toggleDropdown"
                        class="absolute right-3 top-1/2 -translate-y-1/2 text-primary cursor-pointer transition-transform duration-300"
                        :class="{ 'rotate-180': isDropdownOpen }">
                        <i class="fa fa-chevron-down"></i>
                    </div>
                    <!-- 下拉选项列表 -->
                    <div v-show="isDropdownOpen"
                        class="absolute left-0 right-0 top-full mt-1 bg-white border border-border rounded-lg dropdown-shadow z-10">
                        <ul class="py-1">
                            <li v-for="option in meetingTypeOptions" :key="option.value"
                                @click="selectMeetingType(option)" class="px-4 py-2 hover:bg-gray-50 cursor-pointer">
                                {{ option.text }}
                            </li>
                        </ul>
                    </div>
                </div>

                <!-- 自定义会议类型的文件上传区域 -->
                <div v-if="selectedMeetingType === 'custom'" class="mt-4 animate-fadeIn">
                    <div ref="dropArea"
                        class="border border-dashed border-border rounded-lg p-4 text-center bg-gray-50 transition-all duration-300"
                        :class="{ 'border-primary bg-primary/5': isDragOver }" @drop="handleDrop"
                        @dragover.prevent="isDragOver = true" @dragleave.prevent="isDragOver = false"
                        @dragenter.prevent="isDragOver = true">
                        <i class="fa fa-cloud-upload text-2xl text-neutral mb-2"></i>
                        <p class="text-sm text-neutral mb-3">上传自定义的模板文件</p>
                        <p class="text-xs text-neutral-400 mb-4">支持的格式：markdown</p>
                        <input ref="customFileInput" type="file" class="hidden" accept=".md,.markdown"
                            @change="handleFileSelect">
                        <button @click="$refs.customFileInput.click()"
                            class="bg-primary text-white px-4 py-2 rounded-md text-sm hover:bg-primary/90 transition-colors">
                            选择文件
                        </button>
                        <div v-if="fileInfo.show" class="mt-2 text-sm" :class="fileInfo.class">
                            {{ fileInfo.text }}
                        </div>
                    </div>
                </div>
            </div>

            <!-- 个性化要求模块 -->
            <div>
                <label class="block text-neutral mb-2">个性化要求</label>
                <div class="relative">
                    <input v-model="requirements" type="text" placeholder="输入个性化要求" class="form-input-style">
                    <div class="absolute left-3 top-1/2 -translate-y-1/2 text-neutral">
                        <i class="fa fa-heart-o"></i>
                    </div>
                </div>
            </div>

            <!-- 底部操作按钮 -->
            <div class="flex justify-end gap-4 mt-8">
                <button @click="goBack" class="btn-secondary">
                    返回
                </button>
                <button @click="goNext" class="btn-primary">
                    下一步
                </button>
            </div>
            <p v-if="errorMessage" class="text-red-500 text-sm mt-2 text-right">{{ errorMessage }}</p>
        </div>
    </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import axios from 'axios'

export default {
    name: 'TemplatesPage',
    setup() {
        const router = useRouter()
        const route = useRoute()
        const sid = ref(route.query.sid || '')

        // 响应式数据
        const meetingTime = ref('')
        const participants = ref('')
        const recorder = ref('')
        const selectedMeetingType = ref('')
        const requirements = ref('')
        const isDropdownOpen = ref(false)
        const isDragOver = ref(false)
        const customFileInput = ref(null)

        const fileInfo = ref({
            show: false,
            text: '',
            class: ''
        })

        // 会议类型选项
        const meetingTypeOptions = [
            { value: 'progress', text: '项目进度' },
            { value: 'discussion', text: '问题讨论' },
            { value: 'lecture', text: '学习讲座' },
            { value: 'custom', text: '自定义' }
        ]

        // 计算属性
        const selectedMeetingTypeText = computed(() => {
            if (!selectedMeetingType.value) return '选择会议类型'
            const option = meetingTypeOptions.find(opt => opt.value === selectedMeetingType.value)
            return option ? option.text : '选择会议类型'
        })

        // 方法
        const toggleDropdown = () => {
            isDropdownOpen.value = !isDropdownOpen.value
        }

        const selectMeetingType = (option) => {
            selectedMeetingType.value = option.value
            isDropdownOpen.value = false
        }

        const handleDrop = (e) => {
            e.preventDefault()
            isDragOver.value = false

            const files = e.dataTransfer.files
            if (files.length > 0) {
                handleFile(files[0])
            }
        }

        const handleFileSelect = (e) => {
            const files = e.target.files
            if (files.length > 0) {
                handleFile(files[0])
            }
        }

        const handleFile = async (file) => {
            // 仅允许md和markdown格式
            const allowedTypes = ['.md', '.markdown']
            const fileExtension = '.' + file.name.split('.').pop().toLowerCase()

            if (allowedTypes.includes(fileExtension)) {
                try {
                    // 创建FormData并上传文件
                    const formData = new FormData()
                    formData.append('file', file)

                    const sidParam = sid.value ? `?sid=${sid.value}` : ''
                    const response = await axios.post(`/api/upload_custom_template${sidParam}`, formData, { withCredentials: true })

                    if (response.data.success) {
                        fileInfo.value = {
                            show: true,
                            text: '上传成功: ' + file.name,
                            class: 'text-green-500'
                        }
                    } else {
                        fileInfo.value = {
                            show: true,
                            text: '上传失败: ' + response.data.error,
                            class: 'text-red-500'
                        }
                    }
                } catch (error) {
                    fileInfo.value = {
                        show: true,
                        text: '上传出错: 请检查服务器配置',
                        class: 'text-red-500'
                    }
                    console.error('上传错误详情:', error)
                }
            } else {
                fileInfo.value = {
                    show: true,
                    text: '错误: 仅支持.md和.markdown格式',
                    class: 'text-red-500'
                }

                // 清空选中的文件
                if (customFileInput.value) {
                    customFileInput.value.value = ''
                }

                setTimeout(() => {
                    fileInfo.value.show = false
                }, 3000)
            }
        }

        const goBack = () => {
            const sidQuery = sid.value ? `?sid=${sid.value}` : ''
            router.push(`/transcribe${sidQuery}`)
        }

        const errorMessage = ref('')

        const goNext = async () => {
            errorMessage.value = ''
            try {
                const sidParam = sid.value ? `?sid=${sid.value}` : ''
                await axios.post(`/api/save_meeting_type${sidParam}`, {
                    type: selectedMeetingType.value || '未设置'
                }, { withCredentials: true })

                const meetingInfo = {
                    time: meetingTime.value || '未设置',
                    participants: participants.value || '未设置',
                    recorder: recorder.value || '未设置',
                    type: selectedMeetingType.value || '未设置',
                    requirements: requirements.value || ''
                }

                await axios.post(`/api/save_meeting_info${sidParam}`, meetingInfo, { withCredentials: true })
                await axios.post(`/api/result${sidParam}`, null, { withCredentials: true })

                console.log('会议信息保存成功')
                const sidQuery = sid.value ? `?sid=${sid.value}` : ''
                router.push(`/result${sidQuery}`)
            } catch (error) {
                console.error('请求失败:', error)
                errorMessage.value = '保存失败，请检查网络后重试'
            }
        }

        // 点击页面其他地方关闭下拉列表
        const handleClickOutside = (event) => {
            if (isDropdownOpen.value && !event.target.closest('.relative')) {
                isDropdownOpen.value = false
            }
        }

        onMounted(() => {
            const now = new Date()
            const pad = n => String(n).padStart(2, '0')
            meetingTime.value = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}T${pad(now.getHours())}:${pad(now.getMinutes())}`

            // 添加点击外部关闭下拉列表的监听
            document.addEventListener('click', handleClickOutside)
        })

        return {
            meetingTime,
            participants,
            recorder,
            selectedMeetingType,
            requirements,
            isDropdownOpen,
            isDragOver,
            customFileInput,
            fileInfo,
            errorMessage,
            meetingTypeOptions,
            selectedMeetingTypeText,
            toggleDropdown,
            selectMeetingType,
            handleDrop,
            handleFileSelect,
            goBack,
            goNext
        }
    }
}
</script>