import type { AttendanceRecord } from '@/types'

const delay = (ms = 250) => new Promise((res) => setTimeout(res, ms))

export const MOCK_ATTENDANCE: AttendanceRecord[] = [
  { id:1, studentName:'Aarav Mehta', className:'10-A', date:'2026-08-19', status:'Present' },
  { id:2, studentName:'Diya Sharma', className:'10-A', date:'2026-08-19', status:'Present' },
  { id:3, studentName:'Kabir Patel', className:'10-A', date:'2026-08-19', status:'Absent' },
  { id:4, studentName:'Ananya Singh', className:'10-A', date:'2026-08-19', status:'Late' },
  { id:5, studentName:'Vivaan Patel', className:'10-A', date:'2026-08-19', status:'Present' },
  { id:6, studentName:'Rohan Verma', className:'9-B', date:'2026-08-19', status:'Absent' },
  { id:7, studentName:'Isha Reddy', className:'9-B', date:'2026-08-19', status:'Present' },
  { id:8, studentName:'Saanvi Gupta', className:'7-C', date:'2026-08-19', status:'Present' },
]

export async function getAttendance(): Promise<AttendanceRecord[]> { await delay(); return MOCK_ATTENDANCE }
