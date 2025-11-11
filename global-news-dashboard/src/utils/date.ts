import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import 'dayjs/locale/zh-cn'
import { DATE_FORMAT, DATE_FORMAT_SHORT, DATE_FORMAT_TIME } from '@/constants'

dayjs.extend(relativeTime)
dayjs.locale('zh-cn')

export function formatDate(date: string | number | Date, format: string = DATE_FORMAT): string {
  return dayjs(date).format(format)
}

export function formatDateShort(date: string | number | Date): string {
  return dayjs(date).format(DATE_FORMAT_SHORT)
}

export function formatTime(date: string | number | Date): string {
  return dayjs(date).format(DATE_FORMAT_TIME)
}

export function formatRelativeTime(date: string | number | Date): string {
  return dayjs(date).fromNow()
}

export function isToday(date: string | number | Date): boolean {
  return dayjs(date).isSame(dayjs(), 'day')
}

export function isYesterday(date: string | number | Date): boolean {
  return dayjs(date).isSame(dayjs().subtract(1, 'day'), 'day')
}

export function getSmartTimeDisplay(date: string | number | Date): string {
  if (isToday(date)) {
    return formatTime(date)
  }
  if (isYesterday(date)) {
    return `昨天 ${formatTime(date)}`
  }
  const daysDiff = dayjs().diff(dayjs(date), 'day')
  if (daysDiff < 7) {
    return formatRelativeTime(date)
  }
  return formatDateShort(date)
}
