/**
 * 应用入口文件
 */

import { createApp } from 'vue';
import { createPinia } from 'pinia';
import App from './App.vue';
import router from './router';

// 创建应用实例
const app = createApp(App);

// 创建 Pinia 实例
const pinia = createPinia();

// 使用插件
app.use(pinia);
app.use(router);

// 挂载应用
app.mount('#app');










