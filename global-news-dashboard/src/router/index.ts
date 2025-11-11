import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/messages'
  },
  {
    path: '/message-sources',
    name: 'MessageSources',
    component: () => import('@/views/MessageSources/index.vue'),
    meta: {
      title: '消息源'
    }
  },
  {
    path: '/messages',
    name: 'Messages',
    component: () => import('@/views/Messages/index.vue'),
    meta: {
      title: '消息列表'
    }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, _from, next) => {
  if (to.meta.title) {
    document.title = `${to.meta.title} - Global News Dashboard`
  }
  next()
})

export default router
