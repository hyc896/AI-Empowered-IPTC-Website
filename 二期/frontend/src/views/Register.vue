<template>
  <div class="register-container">
    <div class="register-box">
      <div class="register-header">
        <h1>用户注册</h1>
        <p>逐光智慧思政平台</p>
      </div>

      <el-form :model="form" :rules="rules" ref="formRef" class="register-form" label-width="80px">
        <el-form-item label="学号/工号" prop="username">
          <el-input v-model="form.username" placeholder="请输入学号或工号" />
        </el-form-item>

        <el-form-item label="真实姓名" prop="real_name">
          <el-input v-model="form.real_name" placeholder="请输入真实姓名" />
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" placeholder="请输入密码（至少6位）" />
        </el-form-item>

        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input v-model="form.confirmPassword" type="password" placeholder="请再次输入密码" />
        </el-form-item>

        <el-form-item label="身份" prop="role">
          <el-radio-group v-model="form.role">
            <el-radio label="student">学生</el-radio>
            <el-radio label="teacher">教师</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="院系/部门">
          <el-input v-model="form.department" placeholder="可选" />
        </el-form-item>

        <el-form-item label="班级" v-if="form.role === 'student'">
          <el-input v-model="form.class_name" placeholder="可选" />
        </el-form-item>

        <el-form-item label="专业" v-if="form.role === 'student'">
          <el-input v-model="form.major" placeholder="如：法学、新闻传播学、社会学等" />
        </el-form-item>

        <el-form-item label="兴趣特长" v-if="form.role === 'student'">
          <el-input v-model="form.interests" placeholder="如：摄影、写作、辩论等（用于AI生成个性化方案）" />
        </el-form-item>

        <el-form-item label="指导教师" v-if="form.role === 'student'" prop="teacher_id">
          <el-select v-model="form.teacher_id" placeholder="请选择指导教师" clearable filterable style="width:100%">
            <el-option v-for="t in teachers" :key="t.id" :label="`${t.real_name}${t.department ? ' (' + t.department + ')' : ''}`" :value="t.id" />
          </el-select>
        </el-form-item>

        <el-form-item label="邮箱">
          <el-input v-model="form.email" placeholder="可选" />
        </el-form-item>

        <el-form-item label="手机号">
          <el-input v-model="form.phone" placeholder="可选" />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="loading" @click="handleRegister" style="width: 100%">
            注册
          </el-button>
        </el-form-item>

        <div class="login-link">
          已有账号？<el-button text type="primary" @click="goToLogin">立即登录</el-button>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { authAPI } from '@/api'
import { ElMessage } from 'element-plus'

const router = useRouter()
const formRef = ref(null)
const loading = ref(false)
const teachers = ref([])

const form = reactive({
  username: '',
  real_name: '',
  password: '',
  confirmPassword: '',
  role: 'student',
  department: '',
  class_name: '',
  major: '',
  interests: '',
  teacher_id: '',
  email: '',
  phone: ''
})

const validateConfirmPassword = (rule, value, callback) => {
  if (value !== form.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const rules = {
  username: [{ required: true, message: '请输入学号/工号', trigger: 'blur' }],
  real_name: [{ required: true, message: '请输入真实姓名', trigger: 'blur' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少6位', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ],
  role: [{ required: true, message: '请选择身份', trigger: 'change' }]
}

const handleRegister = async () => {
  try {
    await formRef.value.validate()
  } catch (error) {
    return
  }

  loading.value = true
  try {
    const { confirmPassword, ...registerData } = form
    // teacher_id 为空字符串时不发送
    if (!registerData.teacher_id) delete registerData.teacher_id
    await authAPI.selfRegister(registerData)
    ElMessage.success('注册成功，请登录')
    setTimeout(() => {
      router.push('/login')
    }, 1500)
  } catch (error) {
    console.error('注册失败:', error)
    ElMessage.error(error.response?.data?.detail || error.message || '注册失败')
  } finally {
    loading.value = false
  }
}

const goToLogin = () => {
  router.push('/login')
}

onMounted(async () => {
  try {
    teachers.value = await authAPI.getTeachers()
  } catch (e) {
    // 获取教师列表失败不影响注册
  }
})
</script>

<style scoped>
.register-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.register-box {
  width: 500px;
  max-width: 100%;
  padding: 40px;
  background: white;
  border-radius: 10px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
}

.register-header {
  text-align: center;
  margin-bottom: 30px;
}

.register-header h1 {
  font-size: 24px;
  color: #333;
  margin-bottom: 10px;
}

.register-header p {
  font-size: 14px;
  color: #999;
}

.register-form {
  margin-top: 20px;
}

.login-link {
  text-align: center;
  margin-top: 16px;
  font-size: 14px;
  color: #666;
}
</style>
