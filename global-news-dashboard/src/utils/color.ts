/**
 * 颜色工具函数 - 对数映射热力图
 */

interface RGB {
  r: number
  g: number
  b: number
}

interface ColorStop {
  position: number
  color: RGB
}

/**
 * 线性插值函数
 */
function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t
}

/**
 * 对数颜色映射函数
 * 使用对数缩放确保低消息数量时颜色变化明显，高消息数量时趋于饱和
 *
 * @param count 当前国家的消息数量
 * @param maxCount 全球最大消息数量
 * @returns rgba颜色字符串
 */
export function getLogHeatmapColor(count: number, maxCount: number): string {
  // 消息数为0时返回深蓝色（暗）
  if (count === 0 || count === undefined) {
    return 'rgba(30, 58, 138, 0.3)'
  }

  // 使用对数映射：log(count + 1) / log(maxCount + 1)
  // log1p确保count=1时有明显的强度值（约0.11-0.3，取决于maxCount）
  const logIntensity = Math.log1p(count) / Math.log1p(maxCount)

  // 颜色停靠点：深蓝 → 中蓝 → 黄色 → 红色
  const colorStops: ColorStop[] = [
    { position: 0.0, color: { r: 30, g: 58, b: 138 } },   // 深蓝色
    { position: 0.3, color: { r: 59, g: 130, b: 246 } },  // 中蓝色
    { position: 0.6, color: { r: 251, g: 191, b: 36 } },  // 黄色
    { position: 1.0, color: { r: 239, g: 68, b: 68 } }    // 红色
  ]

  // 找到当前强度值对应的两个颜色停靠点
  let lowerStop = colorStops[0]
  let upperStop = colorStops[colorStops.length - 1]

  for (let i = 0; i < colorStops.length - 1; i++) {
    if (logIntensity >= colorStops[i].position && logIntensity <= colorStops[i + 1].position) {
      lowerStop = colorStops[i]
      upperStop = colorStops[i + 1]
      break
    }
  }

  // 计算在当前区间内的插值因子
  const segmentRange = upperStop.position - lowerStop.position
  const t = segmentRange > 0 ? (logIntensity - lowerStop.position) / segmentRange : 0

  // RGB颜色插值
  const r = Math.round(lerp(lowerStop.color.r, upperStop.color.r, t))
  const g = Math.round(lerp(lowerStop.color.g, upperStop.color.g, t))
  const b = Math.round(lerp(lowerStop.color.b, upperStop.color.b, t))

  // 透明度随强度增加：0.5 → 0.8
  const opacity = 0.5 + logIntensity * 0.3

  return `rgba(${r}, ${g}, ${b}, ${opacity})`
}
