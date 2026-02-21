/**
 * 路由配置
 */

import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/HomeView.vue'),
    meta: {
      title: '首页 - AI赋能思政案例库',
    },
  },
  {
    path: '/cases',
    name: 'Cases',
    component: () => import('@/views/CasesView.vue'),
    meta: {
      title: '案例库 - AI赋能思政案例库',
    },
  },
  {
    path: '/cases/:id',
    name: 'CaseDetail',
    component: () => import('@/views/CaseDetailView.vue'),
    meta: {
      title: '案例详情 - AI赋能思政案例库',
    },
  },
  {
    path: '/graph',
    name: 'Graph',
    component: () => import('@/views/GraphView.vue'),
    meta: {
      title: '知识图谱 - AI赋能思政案例库',
    },
  },
  {
    path: '/graph/mindmap/:bookId',
    name: 'MindMap',
    component: () => import('@/views/MindMapView.vue'),
    meta: {
      title: '思维导图 - AI赋能思政案例库',
    },
  },
  {
    path: '/collection-status',
    name: 'CollectionStatus',
    component: () => import('@/views/CollectionStatusView.vue'),
    meta: {
      title: '采集状态 - AI赋能思政案例库',
    },
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFoundView.vue'),
    meta: {
      title: '页面未找到',
    },
  },
];

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition;
    } else {
      return { top: 0 };
    }
  },
});

// 路由守卫
router.beforeEach((to, from, next) => {
  // 设置页面标题
  if (to.meta.title) {
    document.title = to.meta.title as string;
  }

  // 关闭移动端菜单
  // 这里可以添加更多全局逻辑

  next();
});

export default router;










