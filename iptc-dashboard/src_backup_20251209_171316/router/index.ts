import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/cases'
    },
    {
      path: '/cases',
      name: 'Cases',
      component: () => import('@/views/Cases/index.vue'),
      meta: { title: '案例库' }
    },
    {
      path: '/graph',
      name: 'KnowledgeGraph',
      component: () => import('@/views/KnowledgeGraph/index.vue'),
      meta: { title: '知识图谱' }
    }
  ]
})

router.beforeEach((to, from, next) => {
  const title = to.meta.title as string
  if (title) {
    document.title = `${title} - 思政课智能案例系统`
  }
  next()
})

export default router



