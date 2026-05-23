import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import './style.css'
import { applyAppTheme, getInitialAppTheme } from './shared/theme/appTheme'

applyAppTheme(getInitialAppTheme())

const app = createApp(App)

app.use(createPinia())
app.use(router)

app.mount('#app')
