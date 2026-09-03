import type { TimetableSlot } from '@/types'

const delay = (ms = 250) => new Promise((res) => setTimeout(res, ms))

export const MOCK_TIMETABLE: TimetableSlot[] = [
  { day:'Mon', period:'P1', className:'10-A', subject:'Mathematics', teacher:'M. Iyer' },
  { day:'Mon', period:'P2', className:'10-A', subject:'Physics', teacher:'P. Menon' },
  { day:'Tue', period:'P1', className:'10-A', subject:'Chemistry', teacher:'R. Khanna' },
  { day:'Wed', period:'P3', className:'10-A', subject:'English', teacher:'S. Das' },
]

export async function getTimetable(): Promise<TimetableSlot[]> { await delay(); return MOCK_TIMETABLE }
