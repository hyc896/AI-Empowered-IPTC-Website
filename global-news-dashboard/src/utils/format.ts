export function formatNumber(num: number): string {
  if (num >= 1000000) {
    return `${(num / 1000000).toFixed(1)}M`
  }
  if (num >= 1000) {
    return `${(num / 1000).toFixed(1)}K`
  }
  return num.toString()
}

export function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) {
    return text
  }
  return text.slice(0, maxLength) + '...'
}

export function highlightKeyword(text: string, keyword: string): string {
  if (!keyword) {
    return text
  }
  const regex = new RegExp(`(${keyword})`, 'gi')
  return text.replace(regex, '<mark>$1</mark>')
}

export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`
}

export function formatDate(dateString: string | undefined): string {
  if (!dateString) return ''
  const date = new Date(dateString)
  if (isNaN(date.getTime())) return ''
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

export function parseCron(cronExpression: string): string {
  if (!cronExpression) return '未设置'

  const parts = cronExpression.trim().split(/\s+/)

  if (parts.length === 5) {
    const [minute, hour, dayOfMonth, month, dayOfWeek] = parts

    if (minute.startsWith('*/')) {
      const interval = minute.substring(2)
      return `每${interval}分钟一次`
    }

    if (hour.startsWith('*/')) {
      const interval = hour.substring(2)
      return `每${interval}小时一次`
    }

    if (minute !== '*' && hour !== '*' && dayOfMonth === '*' && month === '*' && dayOfWeek === '*') {
      return `每天${hour.padStart(2, '0')}:${minute.padStart(2, '0')}`
    }

    if (minute === '0' && hour === '*' && dayOfMonth === '*' && month === '*' && dayOfWeek === '*') {
      return '每小时整点'
    }

    return cronExpression
  }

  if (parts.length === 6) {
    const [second, minute, hour, dayOfMonth, month, dayOfWeek] = parts

    if (second.startsWith('*/')) {
      const interval = second.substring(2)
      return `每${interval}秒一次`
    }

    if (minute.startsWith('*/')) {
      const interval = minute.substring(2)
      return `每${interval}分钟一次`
    }

    if (hour.startsWith('*/')) {
      const interval = hour.substring(2)
      return `每${interval}小时一次`
    }

    return cronExpression
  }

  return cronExpression
}
