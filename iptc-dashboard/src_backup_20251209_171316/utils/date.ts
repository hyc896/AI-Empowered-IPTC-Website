import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import 'dayjs/locale/zh-cn'

dayjs.extend(relativeTime)
dayjs.locale('zh-cn')

export const formatRelativeTime = (date: string | Date): string => {
  return dayjs(date).fromNow()
}

export const formatDate = (date: string | Date, format = 'YYYY-MM-DD HH:mm'): string => {
  return dayjs(date).format(format)
}

export const formatDateShort = (date: string | Date): string => {
  return dayjs(date).format('YYYY-MM-DD')
}

export const formatDateTime = (date: string | Date): string => {
  return dayjs(date).format('YYYY-MM-DD HH:mm:ss')
}
