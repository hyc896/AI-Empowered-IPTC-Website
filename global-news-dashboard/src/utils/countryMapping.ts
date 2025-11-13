/**
 * 国家名映射工具
 *
 * 功能：
 * - 中文国家名 ↔ GeoJSON英文标准名 双向映射
 * - 用于前端显示中文，同时匹配GeoJSON地图数据
 */

/**
 * 中文国家名 → GeoJSON英文标准名
 *
 * 用途：将后端API返回的中文国家名转换为GeoJSON中的英文名（用于地图匹配）
 */
export const CHINESE_TO_GEOJSON: Record<string, string> = {
  // 东亚
  '中国': 'China',
  '日本': 'Japan',
  '韩国': 'South Korea',
  '朝鲜': 'North Korea',
  '蒙古': 'Mongolia',

  // 东南亚
  '新加坡': 'Singapore',
  '泰国': 'Thailand',
  '越南': 'Vietnam',
  '马来西亚': 'Malaysia',
  '印度尼西亚': 'Indonesia',
  '菲律宾': 'Philippines',
  '缅甸': 'Myanmar',
  '老挝': 'Laos',
  '柬埔寨': 'Cambodia',
  '文莱': 'Brunei',

  // 南亚
  '印度': 'India',
  '巴基斯坦': 'Pakistan',
  '孟加拉国': 'Bangladesh',
  '斯里兰卡': 'Sri Lanka',
  '尼泊尔': 'Nepal',
  '不丹': 'Bhutan',
  '马尔代夫': 'Maldives',

  // 北美
  '美国': 'United States of America',
  '加拿大': 'Canada',
  '墨西哥': 'Mexico',

  // 中美洲
  '古巴': 'Cuba',
  '巴拿马': 'Panama',
  '哥斯达黎加': 'Costa Rica',

  // 南美
  '巴西': 'Brazil',
  '阿根廷': 'Argentina',
  '智利': 'Chile',
  '秘鲁': 'Peru',
  '哥伦比亚': 'Colombia',
  '委内瑞拉': 'Venezuela',

  // 西欧
  '英国': 'United Kingdom',
  '法国': 'France',
  '德国': 'Germany',
  '意大利': 'Italy',
  '西班牙': 'Spain',
  '荷兰': 'Netherlands',
  '比利时': 'Belgium',
  '瑞士': 'Switzerland',
  '奥地利': 'Austria',
  '葡萄牙': 'Portugal',
  '爱尔兰': 'Ireland',
  '卢森堡': 'Luxembourg',

  // 北欧
  '瑞典': 'Sweden',
  '挪威': 'Norway',
  '芬兰': 'Finland',
  '丹麦': 'Denmark',
  '冰岛': 'Iceland',

  // 东欧
  '俄罗斯': 'Russia',
  '乌克兰': 'Ukraine',
  '波兰': 'Poland',
  '捷克': 'Czech Republic',
  '匈牙利': 'Hungary',
  '罗马尼亚': 'Romania',
  '保加利亚': 'Bulgaria',
  '白俄罗斯': 'Belarus',

  // 南欧
  '希腊': 'Greece',
  '塞尔维亚': 'Serbia',
  '克罗地亚': 'Croatia',

  // 中东
  '以色列': 'Israel',
  '沙特阿拉伯': 'Saudi Arabia',
  '阿联酋': 'United Arab Emirates',
  '土耳其': 'Turkey',
  '伊朗': 'Iran',
  '伊拉克': 'Iraq',
  '叙利亚': 'Syria',
  '约旦': 'Jordan',
  '黎巴嫩': 'Lebanon',
  '科威特': 'Kuwait',
  '卡塔尔': 'Qatar',
  '巴林': 'Bahrain',
  '阿曼': 'Oman',
  '也门': 'Yemen',

  // 非洲
  '南非': 'South Africa',
  '埃及': 'Egypt',
  '尼日利亚': 'Nigeria',
  '肯尼亚': 'Kenya',
  '埃塞俄比亚': 'Ethiopia',
  '摩洛哥': 'Morocco',
  '阿尔及利亚': 'Algeria',
  '突尼斯': 'Tunisia',

  // 大洋洲
  '澳大利亚': 'Australia',
  '新西兰': 'New Zealand',
  '斐济': 'Fiji',

  // 中亚
  '哈萨克斯坦': 'Kazakhstan',
  '乌兹别克斯坦': 'Uzbekistan',
  '土库曼斯坦': 'Turkmenistan',
  '吉尔吉斯斯坦': 'Kyrgyzstan',
  '塔吉克斯坦': 'Tajikistan',
  '阿富汗': 'Afghanistan',

  // 特殊标记
  '全球': 'Global',
  '国际': 'International',
  '未知': 'Unknown',
}

/**
 * GeoJSON英文标准名 → 中文显示名
 *
 * 用途：将GeoJSON地图中的英文国家名转换为中文（用于界面显示）
 */
export const GEOJSON_TO_CHINESE: Record<string, string> = {
  // 自动反转CHINESE_TO_GEOJSON映射
  ...Object.fromEntries(
    Object.entries(CHINESE_TO_GEOJSON).map(([chinese, english]) => [english, chinese])
  ),

  // 特殊处理：GeoJSON中的变体名称
  'United States': '美国',
  'USA': '美国',
  'US': '美国',
  'UK': '英国',
  'Britain': '英国',
  'Korea, South': '韩国',
  'Korea, North': '朝鲜',
}

/**
 * 将中文国家名转换为GeoJSON英文名
 *
 * @param chineseName - 中文国家名（如"中国"）
 * @returns GeoJSON英文标准名（如"China"），如果未找到映射则返回原值
 *
 * @example
 * chineseToGeoJSON('中国') // => 'China'
 * chineseToGeoJSON('美国') // => 'United States of America'
 */
export function chineseToGeoJSON(chineseName: string): string {
  return CHINESE_TO_GEOJSON[chineseName] || chineseName
}

/**
 * 将GeoJSON英文名转换为中文显示名
 *
 * @param geoJsonName - GeoJSON英文国家名（如"China"）
 * @returns 中文显示名（如"中国"），如果未找到映射则返回原值
 *
 * @example
 * geoJSONToChinese('China') // => '中国'
 * geoJSONToChinese('United States of America') // => '美国'
 */
export function geoJSONToChinese(geoJsonName: string): string {
  return GEOJSON_TO_CHINESE[geoJsonName] || geoJsonName
}

/**
 * 批量转换：将后端API返回的统计数据（中文key）转换为前端可用格式
 *
 * @param apiStats - 后端API返回的统计对象，key为中文国家名
 * @returns 转换后的对象，包含中文名、英文名、数量的映射
 *
 * @example
 * const apiData = { "中国": 256, "美国": 145 }
 * const result = transformAPIStats(apiData)
 * // result = {
 * //   byChineseName: { "中国": 256, "美国": 145 },
 * //   byGeoJSONName: { "China": 256, "United States of America": 145 }
 * // }
 */
export function transformAPIStats(apiStats: Record<string, number>): {
  byChineseName: Record<string, number>
  byGeoJSONName: Record<string, number>
} {
  const byChineseName = { ...apiStats }
  const byGeoJSONName: Record<string, number> = {}

  for (const [chineseName, count] of Object.entries(apiStats)) {
    const geoJsonName = chineseToGeoJSON(chineseName)
    byGeoJSONName[geoJsonName] = count
  }

  return {
    byChineseName,
    byGeoJSONName
  }
}

/**
 * 常用国家列表（中文）
 * 用于下拉框选项等
 */
export const COMMON_COUNTRIES_CHINESE = [
  '中国',
  '美国',
  '英国',
  '日本',
  '德国',
  '法国',
  '印度',
  '巴西',
  '澳大利亚',
  '加拿大',
  '韩国',
  '俄罗斯',
  '意大利',
  '西班牙',
  '墨西哥',
]
