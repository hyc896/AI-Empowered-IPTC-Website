<template>
  <div class="admin-users">
    <h2 class="page-title">用户管理</h2>
    <div v-if="loading" class="tip">加载中...</div>
    <div v-else>
      <table class="data-table">
        <thead><tr><th>用户名</th><th>姓名</th><th>角色</th><th>状态</th><th>注册时间</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="u in users" :key="u.id">
            <td>{{ u.username }}</td>
            <td>{{ u.real_name || '-' }}</td>
            <td>
              <el-select v-model="u.role" size="small" style="width:90px" @change="updateRole(u)">
                <el-option label="学生" value="student" />
                <el-option label="教师" value="teacher" />
                <el-option label="管理员" value="admin" />
              </el-select>
            </td>
            <td><span :class="['badge', u.is_active ? 'active' : 'inactive']">{{ u.is_active ? '正常' : '禁用' }}</span></td>
            <td>{{ u.created_at ? u.created_at.slice(0, 10) : '-' }}</td>
            <td>-</td>
          </tr>
        </tbody>
      </table>
      <div class="pagination">
        <el-pagination v-model:current-page="page" :page-size="20" :total="total"
          layout="prev, pager, next" @current-change="load" background small />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { adminAPI } from '@/api/index'

const users = ref([])
const loading = ref(true)
const page = ref(1)
const total = ref(0)

async function load() {
  loading.value = true
  try {
    const r = await adminAPI.getUsers({ page: page.value })
    users.value = r.items || []
    total.value = r.total || 0
  } finally {
    loading.value = false
  }
}

async function updateRole(u) {
  try {
    await adminAPI.updateUserRole(u.id, u.role)
    ElMessage.success('角色已更新')
  } catch (e) {
    ElMessage.error('更新失败')
  }
}

onMounted(load)
</script>

<style scoped>
.admin-users { max-width: 960px; }
.page-title { color: #ffd700; margin-bottom: 24px; font-size: 20px; }
.tip { color: rgba(255,255,255,0.4); padding: 16px 0; }
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th, .data-table td { padding: 10px 14px; border-bottom: 1px solid rgba(255,255,255,0.08); text-align: left; }
.data-table th { color: rgba(255,215,0,0.7); font-weight: 600; }
.data-table td { color: rgba(255,255,255,0.8); }
.badge { padding: 2px 8px; border-radius: 8px; font-size: 11px; }
.badge.active { background: rgba(39,174,96,0.2); color: #6fcf97; }
.badge.inactive { background: rgba(235,87,87,0.15); color: #eb5757; }
.pagination { padding: 16px 0; display: flex; justify-content: center; }
</style>
