const CATEGORY_FULL_NAMES = {
  '习概': '习近平新时代中国特色社会主义思想概论',
  '思修': '思想道德基础与法律修养',
  '马原': '马克思主义基本原理概论'
}

export const categoryFullName = (cat) => CATEGORY_FULL_NAMES[cat] || cat
