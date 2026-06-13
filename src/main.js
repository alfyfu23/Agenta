import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import './style.css'

// 导入页面组件
import UploadPage from './views/UploadPage.vue'
import TranscriptionPage from './views/TranscriptionPage.vue'
import TemplatesPage from './views/TemplatesPage.vue'
import ResultPage from './views/ResultPage.vue'

import axios from 'axios'
axios.defaults.withCredentials = true  // 全局允许携带Cookie

// 创建路由
const routes = [
  { path: '/', component: UploadPage },
  { path: '/transcribe', component: TranscriptionPage },
  { path: '/templates', component: TemplatesPage },
  { path: '/result', component: ResultPage }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 创建Vue应用
const app = createApp(App)
app.use(router)
app.mount('#app') 
