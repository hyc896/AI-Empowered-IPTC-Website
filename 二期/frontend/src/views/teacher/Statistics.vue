<template>
  <div class="statistics">
    <div class="page-header">
      <h2>统计分析</h2>
    </div>

    <el-row :gutter="16" class="stats-row">
      <el-col :span="6" v-for="s in summaryStats" :key="s.label">
        <el-card class="stat-card">
          <div class="stat-num" :style="{ color: s.color }">{{ s.value }}</div>
          <div class="stat-label">{{ s.label }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top:20px">
      <el-col :span="12">
        <el-card>
          <template #header><span>实践类型分布</span></template>
          <div ref="typeChartRef" style="height:300px"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header><span>审核状态分布</span></template>
          <div ref="statusChartRef" style="height:300px"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import * as echarts from 'echarts'

const typeChartRef = ref(null)
const statusChartRef = ref(null)

const summaryStats = ref([
  { label: '总提交数', value: 0, color: '#409eff' },
  { label: '待审核', value: 0, color: '#e6a23c' },
  { label: '已通过', value: 0, color: '#67c23a' },
  { label: '未通过', value: 0, color: '#f56c6c' }
])

const initCharts = () => {
  // 实践类型分布饼图
  const typeChart = echarts.init(typeChartRef.value)
  typeChart.setOption({
    tooltip: { trigger: 'item' },
    legend: { bottom: 0 },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      data: [
        { value: 0, name: '写作设计' },
        { value: 0, name: '宣传表达' },
        { value: 0, name: '参观研学' },
        { value: 0, name: '表演体验' },
        { value: 0, name: '交往行动' },
        { value: 0, name: '生产改造' },
        { value: 0, name: '自由申请' }
      ]
    }]
  })

  // 审核状态分布
  const statusChart = echarts.init(statusChartRef.value)
  statusChart.setOption({
    tooltip: { trigger: 'item' },
    legend: { bottom: 0 },
    series: [{
      type: 'pie',
      radius: '60%',
      data: [
        { value: 0, name: '草稿', itemStyle: { color: '#909399' } },
        { value: 0, name: '审核中', itemStyle: { color: '#e6a23c' } },
        { value: 0, name: '已通过', itemStyle: { color: '#67c23a' } },
        { value: 0, name: '未通过', itemStyle: { color: '#f56c6c' } }
      ]
    }]
  })
}

onMounted(initCharts)
</script>

<style scoped>
.statistics { width: 100%; }
.page-header { margin-bottom: 20px; }
.page-header h2 { font-size: 22px; color: #333; }
.stats-row { margin-bottom: 4px; }
.stat-card { text-align: center; padding: 10px; }
.stat-num { font-size: 36px; font-weight: bold; }
.stat-label { font-size: 14px; color: #888; margin-top: 4px; }
</style>
