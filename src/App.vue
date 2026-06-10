<template>
  <div
    id="app"
    class="bg-light text-gray-800 font-sans min-h-screen flex overflow-hidden"
  >
    <!-- 左侧导航栏 -->
    <aside class="w-auto bg-white border-r border-border flex flex-col h-screen">
      <!-- Agenta标识 -->
      <div class="h-16 p-4 md:p-6 border-b border-border min-w-[120px]">
        <h1 class="text-xl font-bold text-primary">
          Agenta
        </h1>
      </div>

      <!-- 导航菜单 -->
      <nav class="flex-1 p-4 space-y-1">
        <div 
          class="sidebar-item active whitespace-nowrap" 
          @click="handleNewMeeting"
        >
          <i class="fa fa-plus w-5 text-center" />
          <span>新建会议</span>
        </div>
      </nav>
    </aside>

    <!-- 主内容区域 -->
    <main class="flex-1 flex flex-col overflow-hidden h-screen">
      <!-- 顶部功能区 -->
      <header class="h-16 border-b border-border flex items-center justify-center">
        <div class="flex items-center gap-2">
          <!-- 四个功能入口 -->
          <div 
            class="topbar-item" 
            :class="currentStep >= 1 ? 'text-primary' : 'text-neutral'"
            style="pointer-events: none;"
          >
            <i class="fa fa-microphone text-lg" />
            <span>上传语音</span>
          </div>
          <div 
            class="topbar-item" 
            :class="currentStep >= 2 ? 'text-primary' : 'text-neutral'"
            style="pointer-events: none;"
          >
            <i class="fa fa-file-text-o text-lg" />
            <span>文字转写</span>
          </div>
          <div 
            class="topbar-item" 
            :class="currentStep >= 3 ? 'text-primary' : 'text-neutral'"
            style="pointer-events: none;"
          >
            <i class="fa fa-th-large text-lg" />
            <span>模板选择</span>
          </div>
          <div 
            class="topbar-item" 
            :class="currentStep >= 4 ? 'text-primary' : 'text-neutral'"
            style="pointer-events: none;"
          >
            <i class="fa fa-file-text text-lg" />
            <span>生成纪要</span>
          </div>
        </div>
      </header>

      <!-- 路由视图 -->
      <section class="flex-1 overflow-y-auto">
        <router-view @step-change="updateStep" />
      </section>
    </main>
  </div>
</template>

<script>
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'

export default {
  name: 'App',
  setup() {
    const route = useRoute()
    const currentStep = ref(1)

    // 根据当前路由计算步骤
    const updateStep = (step) => {
      currentStep.value = step
    }

    // 新建会议处理
    const handleNewMeeting = () => {
      if (confirm('当前操作会放弃未保存的内容，确定要新建会议吗？')) {
        window.location.href = '/'
      }
    }

    // 监听路由变化
    const routeStepMap = {
      '/': 1,
      '/transcribe': 2,
      '/templates': 3,
      '/result': 4
    }

    // 计算当前步骤
    const computedStep = computed(() => {
      return routeStepMap[route.path] || 1
    })

    return {
      currentStep: computedStep,
      updateStep,
      handleNewMeeting
    }
  }
}
</script> 