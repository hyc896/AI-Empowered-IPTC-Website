const CATEGORY_FULL_NAMES = {
  'xi_thought': '习近平新时代中国特色社会主义思想概论',
  'morality': '思想道德与法治',
  'marxism': '马克思主义基本原理'
}

export const categoryFullName = (cat) => CATEGORY_FULL_NAMES[cat] || cat
