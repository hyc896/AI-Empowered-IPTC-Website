<template>
  <div class="admin-users">
    <div class="page-header">
      <h2>用户管理</h2>
      <span class="subtitle">共 {{ total }} 名用户</span>
    </div>
    <div v-if="loading" class="loading">加载中...</div>
    <div v-else>
      <div class="user-list">
        <div class="user-header">
          <span>用户名</span><span>姓名</span><span>角色</span><span>状态</span><span>注册时间</span>
        </div>
        <div class="user-row" v-for="u in users" :key="u.id">
          <span class="uname">{{ u.username }}</span>
          <span class="ureal">{{ u.real_name || '—' }}</span>
          <span>
            <select class="role-select" v-model="u.role" @change="updateRole(u)">
              <option value="student">学生</option>
              <option value="teacher">教师</option>
              <option value="admin">管理员</option>
            </select>
          </span>
          <span>
            <span :class="['status-badge', u.is_active ? 'active' : 'inactive']">
              {{ u.is_active ? '正常' : '禁用' }}
            </span>
          </span>
          <span class="udate">{{ u.created_at ? u.created_at.slice(0,10) : '—' }}</span>
        </div>
      </div>
      <div class="pagination">
        <el-pagination v-model:current-page="page" :page-size="20" :total="total"
          layout="prev, pager, next" @current-change="load" background size="small" />
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
  } finally { loading.value = false }
}

async function updateRole(u) {
  try {
    await adminAPI.updateUserRole(u.id, u.role)
    ElMessage.success('角色已更新')
  } catch (e) { ElMessage.error('更新失败') }
}

onMounted(load)
</script>

<style scoped>
.admin-users { width: 100%; }
.page-header { display: flex; align-items: baseline; gap: 12px; margin-bottom: 24px; }
.page-header h2 { font-size: 22px; font-weight: 700; color: #fff; margin: 0; }
.subtitle { font-size: 13px; color: rgba(255,255,255,0.4); }
.loading { color: rgba(255,255,255,0.4); padding: 32px 0; font-size: 13px; }

.user-list { border-radius: 10px; overflow: hidden; border: 1px solid rgba(255,255,255,0.08); }
.user-header {
  display: grid;
  grid-template-columns: 1.2fr 1fr 0.8fr 0.6fr 1fr;
  padding: 10px 16px;
  background: rgba(0,0,0,0.5);
  font-size: 11px;
  color: rgba(255,215,0,0.6);
  text-transform: uppercase;
  letter-spacing: 1px;
}
.user-row {
  display: grid;
  grid-template-columns: 1.2fr 1fr 0.8fr 0.6fr 1fr;
  padding: 12px 16px;
  font-size: 13px;
  color: rgba(255,255,255,0.8);
  border-top: 1px solid rgba(255,255,255,0.05);
  background: rgba(0,0,0,0.35);
  transition: background 0.15s;
  align-items: center;
}
.user-row:hover { background: rgba(0,0,0,0.5); }
.uname { font-weight: 600; color: #fff; }
.ureal { color: rgba(255,255,255,0.6); }
.udate { color: rgba(255,255,255,0.4); font-size: 12px; }

.role-select {
  background: rgba(255,255,255,0.08);
  border: 1px solid rgba(255,255,255,0.15);
  border-radius: 6px;
  color: #fff;
  padding: 4px 8px;
  font-size: 12px;
  cursor: pointer;
  outline: none;
}
.role-select:focus { border-color: rgba(255,215,0,0.4); }
.role-select option { background: #1a1a1a; }

.status-badge { padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
.status-badge.active { background: rgba(39,174,96,0.15); color: #6fcf97; border: 1px solid rgba(39,174,96,0.25); }
.status-badge.inactive { background: rgba(235,87,87,0.12); color: #eb8787; border: 1px solid rgba(235,87,87,0.2); }

.pagination { padding: 16px 0; display: flex; justify-content: center; }
</style>
