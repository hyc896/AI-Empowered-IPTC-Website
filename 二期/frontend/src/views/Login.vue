<template>
  <main class="login-page">
    <section class="login-shell" aria-label="逐光智慧思政平台登录">
      <div class="brand-panel">
        <div class="brand-lockup">
          <span class="brand-mark">逐</span>
          <div>
            <span class="eyebrow">ZHU GUANG IPTC</span>
            <h1>逐光智慧思政平台</h1>
          </div>
        </div>

        <p class="brand-lead">
          连接思政教学案例、实践场馆与学习过程，让理论学习进入真实场景。
        </p>

        <div class="feature-strip">
          <div>
            <strong>案例库</strong>
            <span>知识点关联与案例检索</span>
          </div>
          <div>
            <strong>实践场馆</strong>
            <span>上海实践资源沉淀</span>
          </div>
          <div>
            <strong>智能流程</strong>
            <span>采集、撞库、生成一体化</span>
          </div>
        </div>
      </div>

      <div class="login-card">
        <div class="card-heading">
          <span class="eyebrow">Account Access</span>
          <h2>登录平台</h2>
          <p>使用学号或工号进入你的教学与实践工作台。</p>
        </div>

        <el-form :model="form" :rules="rules" ref="formRef" class="login-form">
          <el-form-item prop="username">
            <el-input
              v-model="form.username"
              placeholder="请输入学号/工号"
              size="large"
              prefix-icon="User"
              autocomplete="username"
            />
          </el-form-item>

          <el-form-item prop="password">
            <el-input
              v-model="form.password"
              type="password"
              placeholder="请输入密码"
              size="large"
              prefix-icon="Lock"
              show-password
              autocomplete="current-password"
              @keyup.enter="handleLogin"
            />
          </el-form-item>

          <el-form-item>
            <el-button
              class="login-button"
              type="primary"
              size="large"
              :loading="loading"
              @click="handleLogin"
            >
              登录
            </el-button>
          </el-form-item>

          <div class="register-link">
            还没有账号？<el-button text type="primary" @click="goToRegister">立即注册</el-button>
          </div>
        </el-form>
      </div>
    </section>
  </main>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'

const router = useRouter()
const userStore = useUserStore()

const formRef = ref(null)
const loading = ref(false)

const form = reactive({
  username: '',
  password: ''
})

const rules = {
  username: [{ required: true, message: '请输入学号/工号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

const handleLogin = async () => {
  try {
    await formRef.value.validate()
  } catch (error) {
    console.log('表单验证失败:', error)
    return
  }

  loading.value = true
  try {
    await userStore.login(form)
    ElMessage.success('登录成功')
    router.push('/')
  } catch (error) {
    console.error('登录失败:', error)
    const detail = error.response?.data?.detail || error.message || '登录失败'

    // 如果是用户未注册，提示并跳转注册
    if (error.response?.status === 404 || detail.includes('未注册')) {
      ElMessage.error({
        message: detail,
        duration: 3000
      })
      setTimeout(() => {
        router.push('/register')
      }, 1500)
    } else {
      ElMessage.error(detail)
    }
  } finally {
    loading.value = false
  }
}

const goToRegister = () => {
  router.push('/register')
}
</script>

<style scoped>
.login-page {
  min-height: 100dvh;
  position: relative;
  display: grid;
  place-items: center;
  padding: 48px 24px;
  overflow: hidden;
  background:
    linear-gradient(115deg, rgba(5, 8, 12, 0.9), rgba(17, 20, 25, 0.74) 47%, rgba(7, 9, 13, 0.94)),
    url('@/assets/bg-main.webp') center/cover no-repeat fixed;
  color: #f8f2e8;
}

.login-page::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    linear-gradient(rgba(255, 255, 255, 0.035) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.028) 1px, transparent 1px);
  background-size: 72px 72px;
  mask-image: linear-gradient(90deg, rgba(0, 0, 0, 0.7), transparent 68%);
  pointer-events: none;
}

.login-shell {
  position: relative;
  z-index: 1;
  width: min(1120px, 100%);
  display: grid;
  grid-template-columns: minmax(0, 1fr) 420px;
  gap: 40px;
  align-items: center;
}

.brand-panel {
  min-width: 0;
  padding: 18px 0;
}

.brand-lockup {
  display: flex;
  align-items: center;
  gap: 18px;
}

.brand-mark {
  width: 58px;
  height: 58px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  background: #d6b15f;
  color: #151515;
  font-size: 30px;
  font-weight: 900;
  box-shadow: 0 18px 48px rgba(0, 0, 0, 0.32);
}

.eyebrow {
  display: inline-block;
  color: #e2bf74;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0;
  text-transform: uppercase;
}

.brand-panel h1 {
  margin: 6px 0 0;
  font-size: clamp(40px, 5vw, 68px);
  line-height: 1.05;
  font-weight: 900;
  letter-spacing: 0;
  color: #fffaf0;
  text-shadow: 0 18px 42px rgba(0, 0, 0, 0.36);
}

.brand-lead {
  max-width: 620px;
  margin: 28px 0 34px;
  color: rgba(248, 242, 232, 0.78);
  font-size: 18px;
  line-height: 1.9;
}

.feature-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  max-width: 720px;
}

.feature-strip > div {
  min-height: 92px;
  padding: 18px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.06);
  backdrop-filter: blur(14px);
}

.feature-strip strong {
  display: block;
  color: #fffaf0;
  font-size: 16px;
  margin-bottom: 8px;
}

.feature-strip span {
  color: rgba(248, 242, 232, 0.62);
  font-size: 13px;
  line-height: 1.6;
}

.login-card {
  width: 100%;
  padding: 34px;
  border-radius: 8px;
  background: rgba(10, 13, 18, 0.78);
  border: 1px solid rgba(255, 255, 255, 0.12);
  box-shadow: 0 28px 80px rgba(0, 0, 0, 0.36);
  backdrop-filter: blur(22px);
}

.card-heading {
  margin-bottom: 28px;
}

.card-heading h2 {
  margin: 8px 0 10px;
  color: #fffaf0;
  font-size: 30px;
  font-weight: 850;
  letter-spacing: 0;
}

.card-heading p {
  margin: 0;
  color: rgba(248, 242, 232, 0.62);
  font-size: 14px;
  line-height: 1.7;
}

.login-form {
  margin-top: 0;
}

.login-form :deep(.el-form-item) {
  margin-bottom: 20px;
}

.login-form :deep(.el-input__wrapper) {
  min-height: 48px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.08);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.12);
  transition: box-shadow 0.18s ease, background 0.18s ease;
}

.login-form :deep(.el-input__wrapper:hover),
.login-form :deep(.el-input__wrapper.is-focus) {
  background: rgba(255, 255, 255, 0.11);
  box-shadow: inset 0 0 0 1px rgba(226, 191, 116, 0.58), 0 0 0 3px rgba(226, 191, 116, 0.08);
}

.login-form :deep(.el-input__inner) {
  color: #fffaf0;
}

.login-form :deep(.el-input__inner::placeholder),
.login-form :deep(.el-input__prefix),
.login-form :deep(.el-input__suffix) {
  color: rgba(248, 242, 232, 0.48);
}

.login-button {
  width: 100%;
  min-height: 48px;
  border-radius: 8px;
  border-color: #d6b15f;
  background: #d6b15f;
  color: #151515;
  font-weight: 850;
  box-shadow: 0 16px 32px rgba(214, 177, 95, 0.22);
}

.login-button:hover,
.login-button:focus {
  border-color: #e2bf74;
  background: #e2bf74;
  color: #151515;
}

.register-link {
  text-align: center;
  margin-top: 14px;
  font-size: 14px;
  color: rgba(248, 242, 232, 0.62);
}

.register-link :deep(.el-button) {
  color: #e2bf74;
  font-weight: 700;
}

@media (max-width: 900px) {
  .login-page {
    overflow: auto;
    padding: 32px 18px;
  }

  .login-shell {
    grid-template-columns: 1fr;
    gap: 28px;
  }

  .brand-panel h1 {
    font-size: 38px;
  }

  .feature-strip {
    grid-template-columns: 1fr;
  }

  .login-card {
    padding: 26px;
  }
}

@media (max-width: 520px) {
  .brand-lockup {
    align-items: flex-start;
  }

  .brand-mark {
    width: 48px;
    height: 48px;
    font-size: 25px;
  }

  .brand-lead {
    font-size: 16px;
    margin: 22px 0;
  }
}
</style>
