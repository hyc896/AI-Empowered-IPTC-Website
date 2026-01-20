<!--
  实体列表组件
  展示提取的实体和关系
-->
<template>
  <div class="entity-list">
    <el-tabs v-model="activeTab">
      <!-- 实体列表 -->
      <el-tab-pane label="实体" name="entities">
        <div class="stats">
          <el-tag>共 {{ entities.length }} 个实体</el-tag>
        </div>
        <el-table :data="entities" height="400" stripe>
          <el-table-column prop="name" label="名称" width="150" />
          <el-table-column prop="type" label="类型" width="120">
            <template #default="{ row }">
              <el-tag :type="getEntityTagType(row.type)">
                {{ row.type }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="mention_count" label="提及次数" width="100" />
          <el-table-column prop="aliases" label="别名">
            <template #default="{ row }">
              <el-tag
                v-for="alias in row.aliases"
                :key="alias"
                size="small"
                style="margin-right: 4px"
              >
                {{ alias }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- 关系列表 -->
      <el-tab-pane label="关系" name="relations">
        <div class="stats">
          <el-tag>共 {{ relations.length }} 个关系</el-tag>
        </div>
        <el-table :data="relations" height="400" stripe>
          <el-table-column prop="source" label="源实体" width="150" />
          <el-table-column prop="type" label="关系类型" width="150">
            <template #default="{ row }">
              <el-tag type="info">{{ row.type }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="target" label="目标实体" width="150" />
        </el-table>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { Entity, Relation, EntityType } from '@/types'

defineProps<{
  entities: Entity[]
  relations: Relation[]
}>()

const activeTab = ref('entities')

const getEntityTagType = (type: EntityType) => {
  const typeMap: Record<EntityType, any> = {
    Company: 'primary',
    Person: 'success',
    Technology: 'info',
    Product: 'warning',
    Organization: 'danger',
    Event: '',
    Concept: 'info',
    Location: 'warning'
  }
  return typeMap[type] || ''
}
</script>

<style scoped>
.entity-list {
  background: #fff;
  border-radius: 4px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.stats {
  margin-bottom: 12px;
}
</style>
