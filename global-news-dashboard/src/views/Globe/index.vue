<template>
  <div class="globe-view">
    <!-- 控制面板 -->
    <div class="globe-controls">
      <el-card class="control-card">
        <template #header>
          <div class="card-header">
            <span>筛选条件</span>
          </div>
        </template>

        <!-- 渲染质量切换 -->
        <div class="filter-group">
          <label>渲染质量</label>
          <el-button-group class="quality-toggle">
            <el-button
              :type="performanceMode === 'low' ? 'primary' : 'default'"
              size="small"
              @click="switchQuality('low')"
            >
              流畅模式
            </el-button>
            <el-button
              :type="performanceMode === 'high' ? 'primary' : 'default'"
              size="small"
              @click="switchQuality('high')"
            >
              高质量
            </el-button>
          </el-button-group>
        </div>

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
        <div class="stat-item">
          <div class="stat-label">性能</div>
          <div class="stat-value fps-counter">
            {{ fps }} FPS
          </div>
        </div>
      </el-card>
    </div>

    <!-- 热力图图例 -->
    <div class="legend-panel">
      <el-card class="legend-card">
        <div class="legend-title">新闻密度</div>
        <div class="legend-gradient"></div>
        <div class="legend-labels">
          <span>0</span>
          <span>100</span>
          <span>200+</span>
        </div>
      </el-card>
    </div>

    <!-- Globe容器 -->
    <div ref="globeContainerRef" class="globe-container"></div>

    <!-- 加载动画 -->
    <div v-if="loading" class="loading-overlay">
      <el-icon class="is-loading" :size="60">
        <Loading />
      </el-icon>
      <p>正在加载地图数据...</p>
    </div>

    <!-- 消息详情抽屉 -->
    <el-drawer
      v-model="drawerVisible"
      :title="`${selectedCountry} - ${selectedCountryNewsCount}条新闻`"
      direction="rtl"
      size="500px"
    >
      <div v-if="selectedCountryMessages.length > 0" class="message-list">
        <el-card
          v-for="message in selectedCountryMessages"
          :key="message.id"
          class="message-card"
          shadow="hover"
        >
          <!-- 消息源标签 -->
          <div class="message-source">{{ message.source_name }}</div>

          <!-- 标题 -->
          <h4 class="message-title">{{ message.title }}</h4>

          <!-- 内容（可展开/收起） -->
          <div class="message-content">
            <div v-if="expandedMessageId === message.id" class="content-full">
              <p class="content-text">{{ message.content }}</p>
              <el-link @click="expandedMessageId = null" type="primary" class="toggle-link">
                收起
              </el-link>
            </div>
            <div v-else class="content-preview">
              <p class="content-text">
                {{ message.summary || truncateText(message.content, 150) }}
              </p>
              <el-link
                v-if="message.content && message.content.length > 150"
                @click="expandedMessageId = message.id"
                type="primary"
                class="toggle-link"
              >
                展开全文
              </el-link>
            </div>
          </div>

          <!-- 元数据 -->
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

          <!-- 链接 -->
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
import { ref, onMounted, onBeforeUnmount, computed } from 'vue'
import { Loading } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import Globe from 'globe.gl'
// @ts-ignore
import * as topojson from 'topojson-client'
import { useMessageStore } from '@/stores/message'
import type { Message, MessageSource } from '@/types/models'
import { formatDateShort } from '@/utils/date'
import * as geoApi from '@/api/geo'
import { transformAPIStats, geoJSONToChinese } from '@/utils/countryMapping'

const messageStore = useMessageStore()

// 响应式数据
const globeContainerRef = ref<HTMLDivElement | null>(null)
const globe = ref<any>(null)
const loading = ref(true)
const performanceMode = ref<'low' | 'high'>('low')
const filterSourceId = ref<string>()
const dateRange = ref<[string, string]>()
const selectedIndustryTags = ref<string[]>([])
const availableIndustryTags = ref<string[]>([])
const drawerVisible = ref(false)
const selectedCountry = ref('')
const selectedCountryNewsCount = ref(0)
const selectedCountryMessages = ref<any[]>([])
const expandedMessageId = ref<string | null>(null)

// FPS监控
const fps = ref(60)
let fpsCounter = { frames: 0, lastTime: performance.now() }

// 地图数据
const worldGeoData = ref<any>(null)

// 计算属性 - 只显示活跃的消息源
const sources = computed<MessageSource[]>(() => messageStore.activeSources)
const totalNews = ref(0)
const totalCountries = ref(0)

// Mock数据（临时使用，后续替换为真实API）
const countryNewsCount: Record<string, number> = {
  China: 256,
  'United States of America': 389,
  'United Kingdom': 145,
  Germany: 178,
  France: 123,
  Japan: 201,
  India: 167,
  Brazil: 89,
  Australia: 92,
  Canada: 118,
  Russia: 156,
  'South Korea': 134,
  Italy: 98,
  Spain: 87,
  Mexico: 76
}

// 颜色映射函数
const getHeatmapColor = (count: number): string => {
  if (count === 0 || count === undefined) return 'rgba(30, 58, 138, 0.3)'
  if (count < 100) return 'rgba(59, 130, 246, 0.5)'
  if (count < 200) return 'rgba(251, 191, 36, 0.6)'
  return 'rgba(239, 68, 68, 0.7)'
}

// 工具函数
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

// 初始化Globe
const initGlobe = () => {
  if (!globeContainerRef.value) return

  globe.value = Globe()(globeContainerRef.value)
    .globeImageUrl('//unpkg.com/three-globe/example/img/earth-night.jpg')
    .backgroundImageUrl('//unpkg.com/three-globe/example/img/night-sky.png')
    .showAtmosphere(true)
    .atmosphereColor('#00d4ff')
    .atmosphereAltitude(0.1)

  globe.value.pointOfView({ lat: 20, lng: 0, altitude: 2.5 }, 0)

  // 控制器设置
  globe.value.controls().autoRotate = false
  globe.value.controls().enableDamping = true
  globe.value.controls().dampingFactor = 0.1

  // 响应式处理
  window.addEventListener('resize', handleResize)

  // FPS监控
  updateFPS()
}

const handleResize = () => {
  if (globe.value && globeContainerRef.value) {
    globe.value.width(globeContainerRef.value.clientWidth)
    globe.value.height(globeContainerRef.value.clientHeight)
  }
}

const updateFPS = () => {
  fpsCounter.frames++
  const now = performance.now()
  const delta = now - fpsCounter.lastTime
  if (delta >= 1000) {
    fps.value = Math.round((fpsCounter.frames * 1000) / delta)
    fpsCounter.frames = 0
    fpsCounter.lastTime = now
  }
  requestAnimationFrame(updateFPS)
}

// 加载世界地图数据
const loadWorldView = async () => {
  try {
    loading.value = true

    // 加载TopoJSON数据
    const response = await fetch('/world_countries_low.geojson')
    const topoData = await response.json()

    // 转换为GeoJSON
    worldGeoData.value = topojson.feature(topoData, topoData.objects.countries)

    // 调用真实API获取地理统计数据
    const stats = await geoApi.getGeoStatistics({
      source_id: filterSourceId.value || undefined,
      start_date: dateRange.value?.[0] || undefined,
      end_date: dateRange.value?.[1] || undefined,
      industry_tags: selectedIndustryTags.value.length > 0 ? selectedIndustryTags.value.join(',') : undefined
    })

    // 转换中文国家名到GeoJSON英文名
    const { byGeoJSONName } = transformAPIStats(stats.statistics)

    // 为每个国家添加新闻数据和中文显示名
    worldGeoData.value.features.forEach((feature: any) => {
      const geoJsonName = feature.properties.name
      feature.properties.newsCount = byGeoJSONName[geoJsonName] || 0
      feature.properties.displayName = geoJSONToChinese(geoJsonName)
    })

    // 更新全局统计
    totalNews.value = stats.total_messages
    totalCountries.value = stats.total_countries

    // 渲染多边形
    renderWorldPolygons()

    loading.value = false
  } catch (error) {
    console.error('加载地图失败:', error)
    ElMessage.error('加载地图数据失败，请稍后重试')
    loading.value = false
  }
}

// 渲染世界多边形
const renderWorldPolygons = () => {
  if (!globe.value || !worldGeoData.value) return

  const altitude = performanceMode.value === 'low' ? 0.006 : 0.01

  globe.value
    .polygonsData(worldGeoData.value.features)
    .polygonCapColor((d: any) => getHeatmapColor(d.properties.newsCount))
    .polygonSideColor(() => 'rgba(0, 100, 200, 0.1)')
    .polygonStrokeColor(() =>
      performanceMode.value === 'low' ? 'rgba(0, 212, 255, 0.3)' : '#00d4ff'
    )
    .polygonAltitude(altitude)
    .polygonLabel((d: any) => {
      const displayName = d.properties.displayName || d.properties.name
      return `
        <div style="background: rgba(0,0,0,0.9); padding: 8px 12px; border-radius: 6px; color: white;">
          <strong>${displayName}</strong><br>
          <span style="color: #00d4ff;">${d.properties.newsCount || 0} 条新闻</span>
        </div>
      `
    })
    .onPolygonClick(handleCountryClick)
    .onPolygonHover((d: any) => {
      if (globeContainerRef.value) {
        globeContainerRef.value.style.cursor = d ? 'pointer' : 'default'
      }
    })
}

// 点击国家处理
const handleCountryClick = async (d: any) => {
  if (!d) return

  const displayName = d.properties.displayName || d.properties.name
  selectedCountry.value = displayName
  selectedCountryNewsCount.value = d.properties.newsCount || 0

  // 调用真实API获取该国家的新闻列表
  try {
    const response = await geoApi.getMessagesByRegion(displayName, {
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
    ElMessage.error(`获取${displayName}的新闻失败`)
    selectedCountryMessages.value = []
  }

  drawerVisible.value = true
}

// 更新统计数据
const updateStats = () => {
  if (!worldGeoData.value) return

  let total = 0
  worldGeoData.value.features.forEach((f: any) => {
    total += f.properties.newsCount || 0
  })

  totalNews.value = total
  totalCountries.value = worldGeoData.value.features.length
}

// 切换渲染质量
const switchQuality = (mode: 'low' | 'high') => {
  performanceMode.value = mode

  if (globe.value) {
    globe.value.controls().autoRotate = mode === 'high'
    if (mode === 'high') {
      globe.value.controls().autoRotateSpeed = 0.2
    }
  }

  renderWorldPolygons()
}

// 筛选变化处理
const handleFilterChange = async () => {
  // 根据筛选条件重新获取数据
  await loadWorldView()
}

// 生命周期钩子
onMounted(async () => {
  await messageStore.fetchMessageSources()

  // 加载行业标签列表
  try {
    const tagsResponse = await geoApi.getAllIndustryTags()
    availableIndustryTags.value = tagsResponse.tags
  } catch (error) {
    console.error('加载行业标签失败:', error)
  }

  initGlobe()
  await loadWorldView()
})

onBeforeUnmount(() => {
  if (globe.value) {
    globe.value._destructor()
  }
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped lang="scss">
.globe-view {
  position: relative;
  width: 100%;
  height: 100vh;
  background: linear-gradient(135deg, #0a0e27 0%, #1a1d3a 100%);
  overflow: hidden;

  .globe-container {
    width: 100%;
    height: 100%;
  }

  .globe-controls {
    position: absolute;
    top: 20px;
    left: 20px;
    z-index: 100;
    width: 280px;

    .control-card {
      background: rgba(255, 255, 255, 0.05);
      backdrop-filter: blur(10px);
      border: 1px solid rgba(255, 255, 255, 0.1);

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

      .quality-toggle {
        width: 100%;
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

          &.fps-counter {
            font-size: 14px;
            color: #10b981;
          }
        }
      }
    }
  }

  .legend-panel {
    position: absolute;
    bottom: 20px;
    right: 20px;
    z-index: 100;

    .legend-card {
      background: rgba(255, 255, 255, 0.05);
      backdrop-filter: blur(10px);
      border: 1px solid rgba(255, 255, 255, 0.1);

      :deep(.el-card__body) {
        background: transparent;
        padding: 15px 20px;
      }

      .legend-title {
        font-size: 11px;
        color: rgba(255, 255, 255, 0.6);
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 10px;
      }

      .legend-gradient {
        width: 150px;
        height: 20px;
        background: linear-gradient(to right, #1e3a8a, #3b82f6, #fbbf24, #ef4444);
        border-radius: 4px;
      }

      .legend-labels {
        display: flex;
        justify-content: space-between;
        font-size: 10px;
        color: rgba(255, 255, 255, 0.7);
        margin-top: 5px;
      }
    }
  }

  .loading-overlay {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background: rgba(10, 14, 39, 0.9);
    z-index: 200;
    color: white;

    p {
      margin-top: 20px;
      font-size: 14px;
      color: rgba(255, 255, 255, 0.7);
      letter-spacing: 1px;
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

      .message-summary {
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
