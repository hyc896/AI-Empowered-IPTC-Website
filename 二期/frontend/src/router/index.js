import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/Register.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/Home.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/showcase',
    name: 'ShowcaseWall',
    component: () => import('@/views/ShowcaseWall.vue'),
    meta: { requiresAuth: false }
  },
  // 学生端路由
  {
    path: '/student',
    component: () => import('@/layouts/StudentLayout.vue'),
    meta: { requiresAuth: true, role: 'student' },
    children: [
      {
        path: 'knowledge',
        name: 'KnowledgeSelect',
        component: () => import('@/views/student/KnowledgeSelect.vue')
      },
      {
        path: 'practice-options',
        name: 'PracticeOptions',
        component: () => import('@/views/student/PracticeOptions.vue')
      },
      {
        path: 'practice-type',
        name: 'PracticeTypeSelect',
        component: () => import('@/views/student/PracticeTypeSelect.vue')
      },
      {
        path: 'free-apply',
        name: 'FreeApply',
        component: () => import('@/views/student/FreeApply.vue')
      },
      {
        path: 'plan/:id',
        name: 'PlanDetail',
        component: () => import('@/views/student/PlanDetail.vue')
      },
      {
        path: 'submit/:planId',
        name: 'PracticeSubmit',
        component: () => import('@/views/student/PracticeSubmit.vue')
      },
      {
        path: 'my-practices',
        name: 'MyPractices',
        component: () => import('@/views/student/MyPractices.vue')
      },
      {
        path: 'calendar',
        name: 'PracticeCalendar',
        component: () => import('@/views/student/PracticeCalendar.vue')
      },
      {
        path: 'profile',
        name: 'StudentProfile',
        component: () => import('@/views/student/Profile.vue')
      }
    ]
  },
  // 教师端路由
  {
    path: '/teacher',
    component: () => import('@/layouts/TeacherLayout.vue'),
    meta: { requiresAuth: true, role: 'teacher' },
    children: [
      {
        path: 'review',
        name: 'ReviewList',
        component: () => import('@/views/teacher/ReviewList.vue')
      },
      {
        path: 'review/:id',
        name: 'ReviewDetail',
        component: () => import('@/views/teacher/ReviewDetail.vue')
      },
      {
        path: 'statistics',
        name: 'Statistics',
        component: () => import('@/views/teacher/Statistics.vue')
      },
      {
        path: 'venues',
        name: 'VenueManage',
        component: () => import('@/views/teacher/VenueManage.vue')
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const userStore = useUserStore()

  // 检查是否需要登录
  const requiresAuth = to.matched.some(r => r.meta.requiresAuth !== false)
  if (requiresAuth && !userStore.isLoggedIn) {
    return next('/login')
  }

  // 检查角色权限（从匹配的路由链中找到 role 限制）
  const requiredRole = to.matched.find(r => r.meta.role)?.meta.role
  if (requiredRole) {
    if (userStore.user?.role === requiredRole || userStore.isAdmin) {
      return next()
    } else {
      return next('/')
    }
  }

  next()
})

export default router
