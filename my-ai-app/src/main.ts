/**
 * 应用入口 — 挂载 Vue、Pinia、Vue Router
 */
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router/index'
import App from './App.vue'

const app = createApp(App)

app.use(createPinia())
app.use(router)

app.mount('#app')
