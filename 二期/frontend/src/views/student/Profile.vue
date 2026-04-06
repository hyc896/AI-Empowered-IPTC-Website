<template>
  <div class="profile-page">
    <div class="page-header">
      <h2>个人中心</h2>
      <p>完善个人信息，AI将为你生成更贴合专业方向的实践方案</p>
    </div>

    <div class="profile-content">
      <div class="profile-card">
        <div class="card-header">
          <el-avatar :size="56" style="background:#c0392b; font-size: 22px">{{ userStore.user?.real_name?.[0] }}</el-avatar>
          <div class="user-meta">
            <h3>{{ userStore.user?.real_name }}</h3>
            <span class="user-role">{{ userStore.user?.role === 'student' ? '学生' : '教师' }}</span>
            <span class="user-id">{{ userStore.user?.username }}</span>
          </div>
        </div>

        <el-form :model="form" label-width="100px" class="profile-form" @submit.prevent>
          <el-divider content-position="left">基本信息</el-divider>

          <el-form-item label="院系/部门">
            <el-input v-model="form.department" placeholder="请输入院系或部门" />
          </el-form-item>

          <template v-if="userStore.user?.role === 'student'">
            <el-form-item label="专业">
              <el-input v-model="form.major" placeholder="如：法学、新闻传播学、社会学等" />
            </el-form-item>

            <el-form-item label="兴趣特长">
              <el-input
                v-model="form.interests"
                type="textarea"
                :rows="2"
                placeholder="如：摄影、写作、辩论、编程等（AI将据此生成个性化方案）"
              />
            </el-form-item>

            <el-form-item label="指导教师">
              <el-select v-model="form.teacher_id" placeholder="请选择指导教师" clearable filterable style="width:100%">
                <el-option v-for="t in teachers" :key="t.id" :label="`${t.real_name}${t.department ? ' (' + t.department + ')' : ''}`" :value="t.id" />
              </el-select>
            </el-form-item>
          </template>

          <el-divider content-position="left">联系方式</el-divider>

          <el-form-item label="邮箱">
            <el-input v-model="form.email" placeholder="可选" />
          </el-form-item>

          <el-form-item label="手机号">
            <el-input v-model="form.phone" placeholder="可选" />
          </el-form-item>

          <el-form-item>
            <el-button type="primary" :loading="saving" @click="handleSave">保存修改</el-button>
          </el-form-item>
        </el-form>
      </div>

      <div class="profile-card">
        <el-divider content-position="left">修改密码</el-divider>
        <el-form :model="pwdForm" :rules="pwdRules" ref="pwdFormRef" label-width="100px" @submit.prevent>
          <el-form-item label="旧密码" prop="old_password">
            <el-input v-model="pwdForm.old_password" type="password" placeholder="请输入当前密码" />
          </el-form-item>
          <el-form-item label="新密码" prop="new_password">
            <el-input v-model="pwdForm.new_password" type="password" placeholder="请输入新密码（至少6位）" />
          </el-form-item>
          <el-form-item label="确认密码" prop="confirm_password">
            <el-input v-model="pwdForm.confirm_password" type="password" placeholder="请再次输入新密码" />
          </el-form-item>
          <el-form-item>
            <el-button type="warning" :loading="changingPwd" @click="handleChangePwd">修改密码</el-button>
          </el-form-item>
        </el-form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { authAPI } from '@/api'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'

const userStore = useUserStore()
const saving = ref(false)
const changingPwd = ref(false)
const teachers = ref([])
const pwdFormRef = ref(null)

const form = reactive({
  department: userStore.user?.department || '',
  major: userStore.user?.major || '',
  interests: userStore.user?.interests || '',
  teacher_id: userStore.user?.teacher_id || '',
  email: userStore.user?.email || '',
  phone: userStore.user?.phone || ''
})

const pwdForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: ''
})

const pwdRules = {
  old_password: [{ required: true, message: '请输入当前密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码至少6位', trigger: 'blur' }
  ],
  confirm_password: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== pwdForm.new_password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

const handleSave = async () => {
  saving.value = true
  try {
    // 更新个人资料
    const profileData = {
      department: form.department || null,
      major: form.major || null,
      interests: form.interests || null,
      email: form.email || null,
      phone: form.phone || null
    }
    await authAPI.updateProfile(profileData)

    // 如果修改了指导教师
    if (form.teacher_id !== (userStore.user?.teacher_id || '')) {
      await authAPI.updateTeacher(form.teacher_id || null)
    }

    // 刷新用户信息
    await userStore.fetchUserInfo()
    ElMessage.success('个人资料已更新')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

const handleChangePwd = async () => {
  try {
    await pwdFormRef.value.validate()
  } catch {
    return
  }
  changingPwd.value = true
  try {
    await authAPI.changePassword({
      old_password: pwdForm.old_password,
      new_password: pwdForm.new_password
    })
    ElMessage.success('密码修改成功')
    pwdForm.old_password = ''
    pwdForm.new_password = ''
    pwdForm.confirm_password = ''
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '密码修改失败')
  } finally {
    changingPwd.value = false
  }
}

onMounted(async () => {
  if (userStore.user?.role === 'student') {
    try {
      teachers.value = await authAPI.getTeachers()
    } catch {
      // ignore
    }
  }
  // 刷新最新用户信息
  try {
    await userStore.fetchUserInfo()
    form.department = userStore.user?.department || ''
    form.major = userStore.user?.major || ''
    form.interests = userStore.user?.interests || ''
    form.teacher_id = userStore.user?.teacher_id || ''
    form.email = userStore.user?.email || ''
    form.phone = userStore.user?.phone || ''
  } catch {
    // ignore
  }
})
</script>

<style scoped>
.profile-page {
  max-width: 680px;
}
.page-header {
  margin-bottom: 24px;
}
.page-header h2 {
  font-size: 22px;
  color: #333;
  margin: 0 0 6px;
}
.page-header p {
  color: #888;
  font-size: 14px;
  margin: 0;
}
.profile-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.profile-card {
  background: #fff;
  border-radius: 10px;
  padding: 28px 32px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.card-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}
.user-meta h3 {
  font-size: 18px;
  color: #333;
  margin: 0 0 4px;
}
.user-role {
  font-size: 12px;
  background: #f0f2f5;
  color: #666;
  padding: 2px 8px;
  border-radius: 4px;
  margin-right: 8px;
}
.user-id {
  font-size: 12px;
  color: #999;
}
.profile-form {
  margin-top: 8px;
}
</style>
