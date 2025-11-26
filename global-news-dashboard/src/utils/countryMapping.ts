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
  '香港': 'Hong Kong S.A.R.',
  '澳门': 'Macao S.A.R',
  '台湾': 'Taiwan',

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
  '东帝汶': 'East Timor',

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

  // 中美洲和加勒比海
  '古巴': 'Cuba',
  '巴拿马': 'Panama',
  '哥斯达黎加': 'Costa Rica',
  '危地马拉': 'Guatemala',
  '洪都拉斯': 'Honduras',
  '萨尔瓦多': 'El Salvador',
  '尼加拉瓜': 'Nicaragua',
  '伯利兹': 'Belize',
  '牙买加': 'Jamaica',
  '海地': 'Haiti',
  '多米尼加': 'Dominican Republic',
  '巴哈马': 'The Bahamas',
  '巴巴多斯': 'Barbados',
  '特立尼达和多巴哥': 'Trinidad and Tobago',
  '多米尼克': 'Dominica',
  '圣卢西亚': 'Saint Lucia',
  '格林纳达': 'Grenada',
  '圣基茨和尼维斯': 'Saint Kitts and Nevis',
  '圣文森特和格林纳丁斯': 'Saint Vincent and the Grenadines',
  '安提瓜和巴布达': 'Antigua and Barbuda',
  '波多黎各': 'Puerto Rico',

  // 南美
  '巴西': 'Brazil',
  '阿根廷': 'Argentina',
  '智利': 'Chile',
  '秘鲁': 'Peru',
  '哥伦比亚': 'Colombia',
  '委内瑞拉': 'Venezuela',
  '厄瓜多尔': 'Ecuador',
  '玻利维亚': 'Bolivia',
  '巴拉圭': 'Paraguay',
  '乌拉圭': 'Uruguay',
  '圭亚那': 'Guyana',
  '苏里南': 'Suriname',
  '福克兰群岛': 'Falkland Islands',

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
  '摩纳哥': 'Monaco',
  '列支敦士登': 'Liechtenstein',
  '安道尔': 'Andorra',
  '马耳他': 'Malta',
  '圣马力诺': 'San Marino',
  '梵蒂冈': 'Vatican',
  '直布罗陀': 'Gibraltar',

  // 北欧
  '瑞典': 'Sweden',
  '挪威': 'Norway',
  '芬兰': 'Finland',
  '丹麦': 'Denmark',
  '冰岛': 'Iceland',
  '格陵兰': 'Greenland',
  '法罗群岛': 'Faroe Islands',
  '奥兰群岛': 'Aland',

  // 东欧
  '俄罗斯': 'Russia',
  '乌克兰': 'Ukraine',
  '波兰': 'Poland',
  '捷克': 'Czechia',
  '匈牙利': 'Hungary',
  '罗马尼亚': 'Romania',
  '保加利亚': 'Bulgaria',
  '白俄罗斯': 'Belarus',
  '摩尔多瓦': 'Moldova',
  '斯洛伐克': 'Slovakia',
  '立陶宛': 'Lithuania',
  '拉脱维亚': 'Latvia',
  '爱沙尼亚': 'Estonia',

  // 南欧/巴尔干
  '希腊': 'Greece',
  '塞尔维亚': 'Republic of Serbia',
  '克罗地亚': 'Croatia',
  '斯洛文尼亚': 'Slovenia',
  '波黑': 'Bosnia and Herzegovina',
  '波斯尼亚和黑塞哥维那': 'Bosnia and Herzegovina',
  '黑山': 'Montenegro',
  '北马其顿': 'North Macedonia',
  '阿尔巴尼亚': 'Albania',
  '科索沃': 'Kosovo',
  '塞浦路斯': 'Cyprus',
  '北塞浦路斯': 'Northern Cyprus',

  // 高加索
  '格鲁吉亚': 'Georgia',
  '亚美尼亚': 'Armenia',
  '阿塞拜疆': 'Azerbaijan',

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
  '巴勒斯坦': 'Palestine',

  // 北非
  '埃及': 'Egypt',
  '利比亚': 'Libya',
  '突尼斯': 'Tunisia',
  '阿尔及利亚': 'Algeria',
  '摩洛哥': 'Morocco',
  '西撒哈拉': 'Western Sahara',
  '苏丹': 'Sudan',
  '南苏丹': 'South Sudan',

  // 西非
  '尼日利亚': 'Nigeria',
  '加纳': 'Ghana',
  '塞内加尔': 'Senegal',
  '科特迪瓦': 'Ivory Coast',
  '马里': 'Mali',
  '布基纳法索': 'Burkina Faso',
  '尼日尔': 'Niger',
  '几内亚': 'Guinea',
  '贝宁': 'Benin',
  '多哥': 'Togo',
  '塞拉利昂': 'Sierra Leone',
  '利比里亚': 'Liberia',
  '冈比亚': 'Gambia',
  '几内亚比绍': 'Guinea-Bissau',
  '毛里塔尼亚': 'Mauritania',
  '佛得角': 'Cabo Verde',

  // 东非
  '肯尼亚': 'Kenya',
  '埃塞俄比亚': 'Ethiopia',
  '坦桑尼亚': 'United Republic of Tanzania',
  '乌干达': 'Uganda',
  '卢旺达': 'Rwanda',
  '布隆迪': 'Burundi',
  '索马里': 'Somalia',
  '索马里兰': 'Somaliland',
  '厄立特里亚': 'Eritrea',
  '吉布提': 'Djibouti',
  '马达加斯加': 'Madagascar',
  '毛里求斯': 'Mauritius',
  '塞舌尔': 'Seychelles',
  '科摩罗': 'Comoros',

  // 中非
  '刚果民主共和国': 'Democratic Republic of the Congo',
  '刚果': 'Republic of the Congo',
  '中非共和国': 'Central African Republic',
  '喀麦隆': 'Cameroon',
  '乍得': 'Chad',
  '加蓬': 'Gabon',
  '赤道几内亚': 'Equatorial Guinea',
  '圣多美和普林西比': 'São Tomé and Principe',

  // 南非
  '南非': 'South Africa',
  '纳米比亚': 'Namibia',
  '博茨瓦纳': 'Botswana',
  '津巴布韦': 'Zimbabwe',
  '赞比亚': 'Zambia',
  '马拉维': 'Malawi',
  '莫桑比克': 'Mozambique',
  '斯威士兰': 'eSwatini',
  '莱索托': 'Lesotho',
  '安哥拉': 'Angola',

  // 大洋洲
  '澳大利亚': 'Australia',
  '新西兰': 'New Zealand',
  '斐济': 'Fiji',
  '巴布亚新几内亚': 'Papua New Guinea',
  '所罗门群岛': 'Solomon Islands',
  '瓦努阿图': 'Vanuatu',
  '新喀里多尼亚': 'New Caledonia',
  '萨摩亚': 'Samoa',
  '汤加': 'Tonga',
  '密克罗尼西亚': 'Federated States of Micronesia',
  '帕劳': 'Palau',
  '马绍尔群岛': 'Marshall Islands',
  '瑙鲁': 'Nauru',
  '基里巴斯': 'Kiribati',
  '图瓦卢': 'Tuvalu',
  '库克群岛': 'Cook Islands',
  '纽埃': 'Niue',
  '法属波利尼西亚': 'French Polynesia',
  '关岛': 'Guam',
  '北马里亚纳群岛': 'Northern Mariana Islands',
  '诺福克岛': 'Norfolk Island',

  // 中亚
  '哈萨克斯坦': 'Kazakhstan',
  '乌兹别克斯坦': 'Uzbekistan',
  '土库曼斯坦': 'Turkmenistan',
  '吉尔吉斯斯坦': 'Kyrgyzstan',
  '塔吉克斯坦': 'Tajikistan',
  '阿富汗': 'Afghanistan',

  // 海外领地和属地
  '百慕大': 'Bermuda',
  '开曼群岛': 'Cayman Islands',
  '英属维尔京群岛': 'British Virgin Islands',
  '美属维尔京群岛': 'United States Virgin Islands',
  '蒙特塞拉特': 'Montserrat',
  '安圭拉': 'Anguilla',
  '特克斯和凯科斯群岛': 'Turks and Caicos Islands',
  '阿鲁巴': 'Aruba',
  '库拉索': 'Curaçao',
  '荷属圣马丁': 'Sint Maarten',
  '法属圣马丁': 'Saint Martin',
  '圣巴泰勒米': 'Saint Barthelemy',
  '圣皮埃尔和密克隆': 'Saint Pierre and Miquelon',
  '圣赫勒拿': 'Saint Helena',
  '英属印度洋领地': 'British Indian Ocean Territory',
  '法属南部和南极领地': 'French Southern and Antarctic Lands',
  '赫德岛和麦克唐纳群岛': 'Heard Island and McDonald Islands',
  '皮特凯恩群岛': 'Pitcairn Islands',
  '瓦利斯和富图纳': 'Wallis and Futuna',
  '美国本土外小岛屿': 'United States Minor Outlying Islands',
  '南乔治亚和南桑威奇群岛': 'South Georgia and the Islands',

  // 特殊地区
  '南极洲': 'Antarctica',
  '马恩岛': 'Isle of Man',
  '根西岛': 'Guernsey',
  '泽西岛': 'Jersey',

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

  // 特殊处理：GeoJSON中的变体名称和别名
  'United States': '美国',
  'USA': '美国',
  'US': '美国',
  'UK': '英国',
  'Britain': '英国',
  'Korea, South': '韩国',
  'Korea, North': '朝鲜',
  'Czech Republic': '捷克',
  'Serbia': '塞尔维亚',
  'Tanzania': '坦桑尼亚',
  'Congo': '刚果',
  'DR Congo': '刚果民主共和国',
  'DRC': '刚果民主共和国',
  'CAR': '中非共和国',
  'UAE': '阿联酋',
  'Swaziland': '斯威士兰',
  'Côte d\'Ivoire': '科特迪瓦',
  'Cote d\'Ivoire': '科特迪瓦',
  'Cape Verde': '佛得角',
  'Sao Tome and Principe': '圣多美和普林西比',
  'Timor-Leste': '东帝汶',
  'Burma': '缅甸',
  'Hong Kong': '香港',
  'Macau': '澳门',
  'Macedonia': '北马其顿',
  'FYROM': '北马其顿',
  'Bosnia': '波黑',
  'Bosnia-Herzegovina': '波黑',
  'Brunei Darussalam': '文莱',
  'Lao PDR': '老挝',
  'Russian Federation': '俄罗斯',
  'Republic of Korea': '韩国',
  'DPRK': '朝鲜',
  'Vatican City': '梵蒂冈',
  'Holy See': '梵蒂冈',
  'Falklands': '福克兰群岛',
  'Malvinas': '福克兰群岛',
  'Micronesia': '密克罗尼西亚',
  'FSM': '密克罗尼西亚',
  'Papua New Guinea': '巴布亚新几内亚',
  'PNG': '巴布亚新几内亚',
  'Indian Ocean Territories': '印度洋领地',
  'American Samoa': '美属萨摩亚',
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
