<!--
  主页面组件
  整合所有功能模块
-->
<template>
  <MainLayout @upload-success="handleUploadSuccess">
    <div class="home-page">
      <el-row :gutter="24">
        <!-- 左侧：图谱可视化 -->
        <el-col :span="16">
          <GraphViewer v-if="graphData" :data="graphData" />
          <el-empty v-else description="请上传 PDF 文件开始分析" />
        </el-col>

        <!-- 右侧：实体列表 -->
        <el-col :span="8">
          <EntityList
            v-if="entities.length > 0"
            :entities="entities"
            :relations="relations"
          />
          <el-empty v-else description="暂无数据" />
        </el-col>
      </el-row>
    </div>
  </MainLayout>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import MainLayout from '@/components/Layout/MainLayout.vue'
import GraphViewer from '@/components/Graph/GraphViewer.vue'
import EntityList from '@/components/Entity/EntityList.vue'
import { extractEntities } from '@/api/extract'
import { getGraphData } from '@/api/graph'
import type { Entity, Relation } from '@/types'
import type { G6GraphData } from '@/types/graph'

const entities = ref<Entity[]>([])
const relations = ref<Relation[]>([])
const graphData = ref<G6GraphData | null>(null)
const currentFileId = ref<string>('')

const handleUploadSuccess = async (fileId: string) => {
  currentFileId.value = fileId
  await loadGraphData(fileId)
}

const loadGraphData = async (fileId: string) => {
  try {
    const response = await getGraphData(fileId)
    console.log('Graph data response:', response)

    // 后端直接返回 nodes, links, categories
    graphData.value = {
      nodes: response.nodes || [],
      edges: response.links || []
    }

    entities.value = (response.nodes || []).map(node => ({
      name: node.name || node.id,
      type: node.category,
      aliases: [],
      mention_count: node.value || 1
    }))

    relations.value = (response.links || []).map(edge => ({
      source: edge.source,
      target: edge.target,
      type: edge.label
    }))

    ElMessage.success('图谱加载成功')
  } catch (error) {
    ElMessage.error('图谱加载失败')
    console.error(error)
  }
}
</script>

<style scoped>
.home-page {
  height: calc(100vh - 120px);
}

.el-row {
  height: 100%;
}

.el-col {
  height: 100%;
}
</style>
