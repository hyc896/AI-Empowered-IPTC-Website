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
import { ref, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { reviewAPI } from '@/api'

const typeChartRef = ref(null)
const statusChartRef = ref(null)
let typeChart = null
let statusChart = null

const summaryStats = ref([
  { label: '总提交数', value: 0, color: '#409eff' },
  { label: '待审核', value: 0, color: '#e6a23c' },
  { label: '已通过', value: 0, color: '#67c23a' },
  { label: '未通过', value: 0, color: '#f56c6c' }
])

const initCharts = () => {
  // 实践类型分布饼图
  typeChart = echarts.init(typeChartRef.value)
  typeChart.setOption({
    tooltip: { trigger: 'item' },
    legend: { bottom: 0 },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      data: []
    }]
  })

  // 审核状态分布
  statusChart = echarts.init(statusChartRef.value)
  statusChart.setOption({
    tooltip: { trigger: 'item' },
    legend: { bottom: 0 },
    series: [{
      type: 'pie',
      radius: '60%',
      data: []
    }]
  })
}

const fetchStatistics = async () => {
  try {
    const res = await reviewAPI.getStatistics()

    // 更新摘要统计
    summaryStats.value = [
      { label: '总提交数', value: res.total || 0, color: '#409eff' },
      { label: '待审核', value: res.pending || 0, color: '#e6a23c' },
      { label: '已通过', value: res.approved || 0, color: '#67c23a' },
      { label: '未通过', value: res.rejected || 0, color: '#f56c6c' }
    ]

    // 更新实践类型分布图
    if (typeChart && res.type_distribution) {
      typeChart.setOption({
        series: [{
          data: res.type_distribution.map(item => ({
            name: item.name,
            value: item.value
          }))
        }]
      })
    }

    // 更新审核状态分布图
    if (statusChart) {
      statusChart.setOption({
        series: [{
          data: [
            { value: res.draft || 0, name: '草稿', itemStyle: { color: '#909399' } },
            { value: res.pending || 0, name: '待审核', itemStyle: { color: '#e6a23c' } },
            { value: res.approved || 0, name: '已通过', itemStyle: { color: '#67c23a' } },
            { value: res.rejected || 0, name: '未通过', itemStyle: { color: '#f56c6c' } }
          ]
        }]
      })
    }
  } catch (e) {
    console.error('获取统计数据失败', e)
  }
}

onMounted(async () => {
  initCharts()
  await nextTick()
  fetchStatistics()
})
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
