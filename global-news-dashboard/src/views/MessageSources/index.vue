<template>
  <div class="message-sources-view">
    <div class="sources-header">
      <h3>消息源管理</h3>
      <el-button
        type="primary"
        :icon="Plus"
        @click="handleCreateSource"
      >
        新建消息源
      </el-button>
    </div>
    <div v-loading="loading" class="sources-list">
      <MessageSourceCard
        v-for="source in sources"
        :key="source.id"
        :source="source"
        @edit="handleEditSource"
        @delete="handleDeleteSource"
        @toggle="handleToggleSource"
      />
    </div>

    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑消息源' : '新建消息源'"
      width="850px"
    >
      <el-form :model="formData" label-width="100px">
        <el-form-item label="名称">
          <el-input v-model="formData.name" placeholder="如: arXiv学术论文" />
        </el-form-item>
        <el-form-item label="适配器">
          <el-input v-model="formData.adapter_name" placeholder="如: ArxivAdapter" />
        </el-form-item>
        <el-form-item label="调度计划">
          <el-input v-model="formData.schedule" placeholder="如: 0 */6 * * *" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="formData.is_active" />
        </el-form-item>

        <el-form-item v-if="currentPlugin" label="配置">
          <component
            :is="currentPlugin.ConfigForm"
            v-model="formData.config"
          />
        </el-form-item>
        <el-form-item v-else-if="formData.adapter_name" label="配置(JSON)">
          <el-input
            v-model="configJson"
            type="textarea"
            :rows="6"
            placeholder='{"key": "value"}'
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useMessageStore } from '@/stores'
import type { MessageSource } from '@/types/models'
import MessageSourceCard from '@/components/common/MessageSourceCard.vue'
import { getPlugin } from '@/plugins/message-sources'

const messageStore = useMessageStore()

const sources = computed(() => messageStore.sources)

const loading = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const formData = ref<{
  id: string
  name: string
  adapter_name: string
  schedule: string
  is_active: boolean
  config?: Record<string, any>
}>({
  id: '',
  name: '',
  adapter_name: '',
  schedule: '',
  is_active: true,
  config: undefined
})

const currentPlugin = computed(() => {
  return formData.value.adapter_name ? getPlugin(formData.value.adapter_name) : null
})

const configJson = ref('')

onMounted(async () => {
  await fetchData()
})

const fetchData = async () => {
  loading.value = true
  try {
    await messageStore.fetchMessageSources()
  } catch (error) {
    ElMessage.error('加载消息源失败')
  } finally {
    loading.value = false
  }
}

const handleCreateSource = () => {
  isEdit.value = false
  formData.value = {
    id: '',
    name: '',
    adapter_name: '',
    schedule: '',
    is_active: true
  }
  dialogVisible.value = true
}

const handleEditSource = (source: MessageSource) => {
  isEdit.value = true
  formData.value = {
    id: source.id,
    name: source.name,
    adapter_name: source.adapter_name,
    schedule: source.schedule || '',
    is_active: source.is_active,
    config: source.config || undefined
  }
  if (source.config && !getPlugin(source.adapter_name)) {
    configJson.value = JSON.stringify(source.config, null, 2)
  } else {
    configJson.value = ''
  }
  dialogVisible.value = true
}

const handleDeleteSource = async (sourceId: string) => {
  try {
    await messageStore.deleteMessageSource(sourceId)
    ElMessage.success('删除成功')
    await fetchData()
  } catch (error) {
    ElMessage.error('删除失败')
  }
}

const handleToggleSource = async (sourceId: string, isActive: boolean) => {
  try {
    await messageStore.updateMessageSource(sourceId, { is_active: isActive })
    ElMessage.success('更新成功')
    await fetchData()
  } catch (error) {
    ElMessage.error('更新失败')
  }
}

const handleSubmit = async () => {
  try {
    let finalConfig = formData.value.config

    if (!currentPlugin.value && configJson.value) {
      try {
        finalConfig = JSON.parse(configJson.value)
      } catch (e) {
        ElMessage.error('配置JSON格式错误')
        return
      }
    }

    if (currentPlugin.value && finalConfig) {
      const validation = currentPlugin.value.validateConfig(finalConfig)
      if (!validation.valid) {
        ElMessage.error(validation.error || '配置验证失败')
        return
      }
    }

    if (isEdit.value) {
      await messageStore.updateMessageSource(formData.value.id, {
        name: formData.value.name,
        schedule: formData.value.schedule,
        is_active: formData.value.is_active,
        config: finalConfig
      })
      ElMessage.success('更新成功')
    } else {
      await messageStore.createMessageSource({
        name: formData.value.name,
        adapter_name: formData.value.adapter_name,
        schedule: formData.value.schedule,
        is_active: formData.value.is_active,
        config: finalConfig
      })
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    await fetchData()
  } catch (error) {
    ElMessage.error(isEdit.value ? '更新失败' : '创建失败')
  }
}
</script>

<style scoped lang="scss">
.message-sources-view {
  padding: 20px;

  .sources-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 20px;

    h3 {
      font-size: 20px;
      font-weight: 600;
      color: var(--text-primary);
    }
  }

  .sources-list {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
    gap: 16px;
  }
}
</style>
