<template>
  <div class="globe-2d-view">
    <!-- 控制面板 -->
    <div class="control-panel" :class="{ collapsed: controlPanelCollapsed }">
      <!-- 收缩/展开按钮 -->
      <div class="toggle-button" @click="controlPanelCollapsed = !controlPanelCollapsed">
        <el-icon :size="20">
          <component :is="controlPanelCollapsed ? 'DArrowRight' : 'DArrowLeft'" />
        </el-icon>
      </div>

      <el-card v-show="!controlPanelCollapsed" class="control-card">
        <template #header>
          <div class="card-header">
            <span>筛选条件</span>
          </div>
        </template>

        <!-- 消息源筛选 -->
        <div class="filter-group">
          <label>消息来源</label>
          <el-select
            v-model="filterSourceId"
            placeholder="全部来源"
            clearable
            size="small"
            @change="handleFilterChange"
          >
            <el-option
              v-for="source in sources"
              :key="source.id"
              :label="source.display_name || source.name"
              :value="source.id"
            />
          </el-select>
        </div>

        <!-- 时间范围 -->
        <div class="filter-group">
          <label>时间范围</label>
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            size="small"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            @change="handleFilterChange"
          />
        </div>

        <!-- 行业标签筛选 -->
        <div class="filter-group">
          <label>行业标签</label>
          <el-select
            v-model="selectedIndustryTags"
            placeholder="全部行业"
            multiple
            clearable
            collapse-tags
            size="small"
            @change="handleFilterChange"
          >
            <el-option
              v-for="tag in availableIndustryTags"
              :key="tag"
              :label="tag"
              :value="tag"
            />
          </el-select>
        </div>
      </el-card>
    </div>

    <!-- 统计面板 -->
    <div class="stats-panel">
      <el-card class="stats-card">
        <div class="stat-item">
          <div class="stat-label">全球新闻</div>
          <div class="stat-value">
            {{ totalNews }}<span class="unit">条</span>
          </div>
        </div>
        <div class="stat-item">
          <div class="stat-label">覆盖国家</div>
          <div class="stat-value">
            {{ totalCountries }}<span class="unit">个</span>
          </div>
        </div>
      </el-card>
    </div>

    <!-- ECharts地图容器 -->
    <v-chart
      v-if="mapReady"
      ref="chartRef"
      class="chart"
      :option="chartOption"
      :loading="loading"
      @click="handleMapClick"
      @mouseover="handleMouseOver"
      @mouseout="handleMouseOut"
      autoresize
    />

    <!-- AI标签实时观察栏 -->
    <AITagsObserver />

    <!-- AI日报抽屉 -->
    <AIDailyReportDrawer />

    <!-- 消息详情抽屉 -->
    <el-drawer
      v-model="drawerVisible"
      :title="`${selectedCountry} - ${selectedCountryNewsCount}条新闻`"
      direction="rtl"
      size="500px"
      @close="handleDrawerClose"
    >
      <div v-if="selectedCountryMessages.length > 0" class="message-list">
        <el-card
          v-for="message in selectedCountryMessages"
          :key="message.id"
          class="message-card"
          shadow="hover"
        >
          <div class="message-source">{{ message.source_name }}</div>
          <h4 class="message-title">{{ message.title }}</h4>
          <div class="message-content">
            <p class="content-text">
              {{ truncateText(message.summary || message.content, 150) }}
            </p>
          </div>
          <div class="message-meta">
            <span>📅 {{ formatDate(message.published_at) }}</span>
            <el-tag
              v-for="tag in parseIndustryTags(message.industry_tags)"
              :key="tag"
              size="small"
              type="info"
            >
              {{ tag }}
            </el-tag>
          </div>
          <div v-if="message.url" class="message-actions">
            <el-link :href="message.url" target="_blank" type="primary">
              🔗 查看原文
            </el-link>
          </div>
        </el-card>
      </div>
      <el-empty v-else description="暂无新闻数据" />
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { MapChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  VisualMapComponent,
  GeoComponent
} from 'echarts/components'
import VChart from 'vue-echarts'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { DArrowLeft, DArrowRight } from '@element-plus/icons-vue'
import { useMessageStore } from '@/stores/message'
import type { MessageSource } from '@/types/models'
import { formatDateShort } from '@/utils/date'
import * as geoApi from '@/api/geo'
import { transformAPIStats, geoJSONToChinese } from '@/utils/countryMapping'
import { geoNaturalEarth1 } from 'd3-geo'
import AITagsObserver from '@/components/AITagsObserver.vue'
import AIDailyReportDrawer from '@/components/AIDailyReportDrawer.vue'

use([
  CanvasRenderer,
  MapChart,
  TitleComponent,
  TooltipComponent,
  VisualMapComponent,
  GeoComponent
])

const messageStore = useMessageStore()

const chartRef = ref()
const loading = ref(true)
const mapReady = ref(false)
const filterSourceId = ref<string>()
const dateRange = ref<[string, string]>()
const selectedIndustryTags = ref<string[]>(['人工智能'])
const availableIndustryTags = ref<string[]>([])
const drawerVisible = ref(false)
const controlPanelCollapsed = ref(true)  // 默认收起
const selectedCountry = ref('')
const selectedCountryNewsCount = ref(0)
const selectedCountryMessages = ref<any[]>([])
const totalNews = ref(0)
const totalCountries = ref(0)
const selectedCountryGeoName = ref<string>('')  // 新增：保存选中国家的英文名

const mapData = ref<Array<{ name: string; value: number }>>([])

const sources = computed<MessageSource[]>(() => messageStore.activeSources)

// 计算地图数据中的最大消息数量（用于对数映射）
const maxCount = computed(() => {
  if (mapData.value.length === 0) return 1
  return Math.max(...mapData.value.map(item => item.value || 0))
})

const chartOption = computed(() => ({
  title: {
    text: '全球新闻热力图',
    left: 'center',
    top: 10,
    textStyle: {
      color: '#fff',
      fontSize: 24,
      fontWeight: 'bold'
    }
  },
  tooltip: {
    trigger: 'item',
    formatter: (params: any) => {
      const geoJsonName = params.name
      const chineseName = geoJSONToChinese(geoJsonName)
      const newsCount = params.data?.value || 0
      return `
        <div style="background: rgba(0,0,0,0.9); padding: 8px 12px; border-radius: 6px; color: white;">
          <strong>${chineseName}</strong><br>
          <span style="color: #00d4ff;">${newsCount} 条新闻</span>
        </div>
      `
    },
    backgroundColor: 'transparent',
    borderColor: 'transparent',
    borderWidth: 0,
    textStyle: {
      color: '#fff'
    }
  },
  visualMap: {
    type: 'piecewise',
    min: 0,
    max: maxCount.value,
    text: ['高', '低'],
    pieces: [
      { min: 200, label: '200+', color: 'rgba(239, 68, 68, 0.8)' },
      { min: 100, max: 199, label: '100-199', color: 'rgba(251, 146, 60, 0.75)' },
      { min: 50, max: 99, label: '50-99', color: 'rgba(251, 191, 36, 0.7)' },
      { min: 10, max: 49, label: '10-49', color: 'rgba(96, 165, 250, 0.65)' },
      { min: 1, max: 9, label: '1-9', color: 'rgba(37, 99, 235, 0.55)' },
      { value: 0, label: '无数据', color: 'rgba(30, 58, 138, 0.3)' }
    ],
    textStyle: {
      color: '#fff'
    },
    left: 20,
    bottom: 40,
    itemWidth: 20,
    itemHeight: 14,
    orient: 'vertical'
  },
  series: [
    {
      name: '新闻数量',
      type: 'map',
      map: 'world',
      roam: true,
      projection: {
        project: (point: [number, number]) => geoNaturalEarth1()(point),
        unproject: (point: [number, number]) => geoNaturalEarth1().invert!(point)
      },
      emphasis: {
        label: {
          show: true,
          color: '#fff',
          fontWeight: 'bold'
        },
        itemStyle: {
          areaColor: '#00d4ff',
          borderColor: '#fff',
          borderWidth: 2,
          shadowBlur: 10,
          shadowColor: 'rgba(0, 212, 255, 0.5)'
        }
      },
      select: {
        label: {
          show: true,
          color: '#fff',
          fontWeight: 'bold'
        },
        itemStyle: {
          areaColor: '#fbbf24',
          borderColor: '#fff',
          borderWidth: 2,
          shadowBlur: 15,
          shadowColor: 'rgba(251, 191, 36, 0.7)'
        }
      },
      selectedMode: 'single',
      itemStyle: {
        borderColor: 'rgba(0, 212, 255, 0.3)',
        borderWidth: 0.5,
        areaColor: 'rgba(30, 58, 138, 0.3)'
      },
      label: {
        show: false
      },
      data: mapData.value
    }
  ],
  backgroundColor: 'transparent'
}))

const truncateText = (text: string, maxLength: number): string => {
  if (!text) return ''
  return text.length > maxLength ? text.substring(0, maxLength) + '...' : text
}

const formatDate = (dateStr: string): string => {
  if (!dateStr) return ''
  return formatDateShort(dateStr)
}

const parseIndustryTags = (tags: string): string[] => {
  if (!tags) return []
  return tags.split(',').map((t: string) => t.trim()).filter(Boolean)
}

const loadWorldMap = async () => {
  try {
    // 加载世界地图GeoJSON（直接使用，无需TopoJSON转换）
    const worldResponse = await fetch('/world_countries_clean.geojson')
    const worldGeoJson = await worldResponse.json()

    // 加载符合中国标准的中国地图（完整版，包含南海诸岛和藏南地区）
    const chinaResponse = await fetch('/china.json')
    const chinaData = await chinaResponse.json()

    // 从世界地图中移除不完整的中国区域
    worldGeoJson.features = worldGeoJson.features.filter((feature: any) => {
      const name = feature.properties.name
      // 移除China和Taiwan，使用完整的中国地图替换
      return name !== 'China' && name !== 'Taiwan'
    })

    // 添加完整的中国地图（符合中国标准，包含南海诸岛）
    if (chinaData.features && chinaData.features.length > 0) {
      // 修改properties以匹配world地图的命名规范
      const chinaFeature = {
        ...chinaData.features[0],
        properties: {
          ...chinaData.features[0].properties,
          name: 'China'  // 使用英文名以匹配数据映射
        }
      }
      worldGeoJson.features.push(chinaFeature)
    }

    echarts.registerMap('world', worldGeoJson)

    console.log('世界地图加载成功（使用标准GeoJSON格式，修复了Fiji和Russia的失真问题）')
    mapReady.value = true
    return true
  } catch (error) {
    console.error('加载世界地图失败:', error)
    ElMessage.error('加载地图数据失败')
    return false
  }
}

const loadStatistics = async () => {
  try {
    loading.value = true

    const stats = await geoApi.getGeoStatistics({
      source_id: filterSourceId.value || undefined,
      start_date: dateRange.value?.[0] || undefined,
      end_date: dateRange.value?.[1] || undefined,
      industry_tags: selectedIndustryTags.value.length > 0 ? selectedIndustryTags.value.join(',') : undefined
    })

    const { byGeoJSONName } = transformAPIStats(stats.statistics)

    mapData.value = Object.entries(byGeoJSONName).map(([name, value]) => ({
      name,
      value
    }))

    totalNews.value = stats.total_messages
    totalCountries.value = stats.total_countries

    loading.value = false
  } catch (error) {
    console.error('加载统计数据失败:', error)
    ElMessage.error('加载统计数据失败')
    loading.value = false
  }
}

const handleMapClick = async (params: any) => {
  // 标记这次点击在国家区域上（用于区分海洋点击）
  lastClickOnCountry = true

  // 点击国家区域
  const geoJsonName = params.name
  const chineseName = geoJSONToChinese(geoJsonName)

  selectedCountry.value = chineseName
  selectedCountryGeoName.value = geoJsonName
  selectedCountryNewsCount.value = params.data.value || 0

  // 触发ECharts选中状态
  if (chartRef.value) {
    chartRef.value.dispatchAction({
      type: 'select',
      seriesIndex: 0,
      name: geoJsonName
    })
  }

  try {
    const response = await geoApi.getMessagesByRegion(chineseName, {
      source_id: filterSourceId.value || undefined,
      start_date: dateRange.value?.[0] || undefined,
      end_date: dateRange.value?.[1] || undefined,
      industry_tags: selectedIndustryTags.value.length > 0 ? selectedIndustryTags.value.join(',') : undefined,
      limit: 50,
      offset: 0
    })
    selectedCountryMessages.value = response.items
  } catch (error) {
    console.error('获取国家消息失败:', error)
    ElMessage.error(`获取${chineseName}的新闻失败`)
    selectedCountryMessages.value = []
  }

  drawerVisible.value = true
}

// 鼠标悬停事件处理
const handleMouseOver = (params: any) => {
  if (params.componentType === 'series' && params.seriesType === 'map') {
    if (chartRef.value) {
      const chartInstance = chartRef.value
      const dom = chartInstance.$el
      if (dom) {
        dom.style.cursor = 'pointer'
      }
    }
  }
}

// 鼠标移出事件处理
const handleMouseOut = (params: any) => {
  if (chartRef.value) {
    const chartInstance = chartRef.value
    const dom = chartInstance.$el
    if (dom) {
      dom.style.cursor = 'default'
    }
  }
}

// 抽屉关闭时清除地图选中状态
const handleDrawerClose = () => {
  if (chartRef.value && selectedCountryGeoName.value) {
    chartRef.value.dispatchAction({
      type: 'unselect',
      seriesIndex: 0,
      name: selectedCountryGeoName.value
    })
    selectedCountryGeoName.value = ''
  }
}

const handleFilterChange = async () => {
  // 清除选中状态
  selectedCountryGeoName.value = ''
  if (chartRef.value) {
    chartRef.value.dispatchAction({
      type: 'unselect',
      seriesIndex: 0
    })
  }
  await loadStatistics()
}

// 处理全球新闻点击（点击海洋/空白区域）
const handleGlobalClick = async () => {
  selectedCountry.value = '全球'
  selectedCountryGeoName.value = ''
  selectedCountryNewsCount.value = totalNews.value

  // 清除任何现有的选中状态
  if (chartRef.value) {
    chartRef.value.dispatchAction({
      type: 'unselect',
      seriesIndex: 0
    })
  }

  try {
    const response = await geoApi.getMessagesByRegion('全球', {
      source_id: filterSourceId.value || undefined,
      start_date: dateRange.value?.[0] || undefined,
      end_date: dateRange.value?.[1] || undefined,
      industry_tags: selectedIndustryTags.value.length > 0 ? selectedIndustryTags.value.join(',') : undefined,
      limit: 50,
      offset: 0
    })
    selectedCountryMessages.value = response.items
  } catch (error) {
    console.error('获取全球消息失败:', error)
    ElMessage.error('获取全球新闻失败')
    selectedCountryMessages.value = []
  }

  drawerVisible.value = true
}

// 记录最后点击是否在国家区域上
let lastClickOnCountry = false

onMounted(async () => {
  await messageStore.fetchMessageSources()

  try {
    const tagsResponse = await geoApi.getAllIndustryTags()
    availableIndustryTags.value = tagsResponse.tags
  } catch (error) {
    console.error('加载行业标签失败:', error)
  }

  const mapLoaded = await loadWorldMap()
  if (mapLoaded) {
    await loadStatistics()

    // 等待图表渲染完成后，监听空白区域点击
    setTimeout(() => {
      if (chartRef.value) {
        const chart = chartRef.value
        // 使用getZr()监听底层canvas的点击事件
        chart.getZr().on('click', (params: any) => {
          // 如果没有点击在国家区域上，显示全球新闻
          if (!lastClickOnCountry) {
            handleGlobalClick()
          }
          // 重置标记
          lastClickOnCountry = false
        })
      }
    }, 100)
  }
})
</script>

<style scoped lang="scss">
.globe-2d-view {
  position: relative;
  width: 100%;
  height: 100vh;
  background: linear-gradient(135deg, #0a0e27 0%, #1a1d3a 100%);
  overflow: hidden;

  .chart {
    width: 100%;
    height: 100%;
  }

  .control-panel {
    position: absolute;
    top: 20px;
    left: 20px;
    z-index: 100;
    width: 280px;
    transition: all 0.3s ease;

    &.collapsed {
      width: 50px;
    }

    .toggle-button {
      position: absolute;
      right: -15px;
      top: 10px;
      width: 30px;
      height: 30px;
      background: rgba(255, 255, 255, 0.1);
      backdrop-filter: blur(10px);
      border: 1px solid rgba(255, 255, 255, 0.2);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      transition: all 0.3s ease;
      color: white;
      z-index: 101;

      &:hover {
        background: rgba(255, 255, 255, 0.2);
        transform: scale(1.1);
      }
    }

    .control-card {
      background: rgba(255, 255, 255, 0.05);
      backdrop-filter: blur(10px);
      border: 1px solid rgba(255, 255, 255, 0.1);
      transition: opacity 0.3s ease;

      :deep(.el-card__header) {
        background: transparent;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        color: white;
      }

      :deep(.el-card__body) {
        background: transparent;
      }
    }

    .filter-group {
      margin-bottom: 16px;

      &:last-child {
        margin-bottom: 0;
      }

      label {
        display: block;
        font-size: 12px;
        color: rgba(255, 255, 255, 0.7);
        margin-bottom: 8px;
        text-transform: uppercase;
        letter-spacing: 1px;
      }

      :deep(.el-select),
      :deep(.el-date-editor) {
        width: 100%;
      }
    }
  }

  .stats-panel {
    position: absolute;
    top: 20px;
    right: 20px;
    z-index: 100;
    min-width: 200px;

    .stats-card {
      background: rgba(255, 255, 255, 0.05);
      backdrop-filter: blur(10px);
      border: 1px solid rgba(255, 255, 255, 0.1);

      :deep(.el-card__body) {
        background: transparent;
        padding: 20px;
      }

      .stat-item {
        margin-bottom: 15px;

        &:last-child {
          margin-bottom: 0;
        }

        .stat-label {
          font-size: 11px;
          color: rgba(255, 255, 255, 0.6);
          text-transform: uppercase;
          letter-spacing: 1px;
          margin-bottom: 5px;
        }

        .stat-value {
          font-size: 28px;
          font-weight: 700;
          color: #fff;
          text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);

          .unit {
            font-size: 14px;
            color: rgba(255, 255, 255, 0.6);
            margin-left: 5px;
          }
        }
      }
    }
  }

  :deep(.el-drawer) {
    background: #f5f5f5;
  }

  .message-list {
    .message-card {
      margin-bottom: 16px;

      &:last-child {
        margin-bottom: 0;
      }

      .message-source {
        display: inline-block;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        font-size: 11px;
        padding: 4px 10px;
        border-radius: 12px;
        margin-bottom: 10px;
        font-weight: 600;
      }

      .message-title {
        font-size: 16px;
        font-weight: 700;
        color: #1a1d3a;
        margin-bottom: 10px;
        line-height: 1.4;
      }

      .message-content {
        font-size: 14px;
        color: #666;
        line-height: 1.6;
        margin-bottom: 12px;
      }

      .message-meta {
        display: flex;
        align-items: center;
        gap: 10px;
        flex-wrap: wrap;
        font-size: 12px;
        color: #999;
        margin-bottom: 12px;
      }

      .message-actions {
        padding-top: 12px;
        border-top: 1px solid #e0e0e0;
      }
    }
  }
}
</style>
