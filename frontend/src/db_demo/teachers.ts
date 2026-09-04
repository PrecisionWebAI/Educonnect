import type { Teacher } from '@/types'

const delay = (ms =  250) => new Promise((res) => setTimeout(res, ms))

export const MOCK_TEACHERS: Teacher[] = [
  { id:1, staffCode:'T-101', name:'M. Iyer', subject:'Mathematics', department:'Science', phone:'98xxxx201', email:'m.iyer@EduConnect.local', status:'Active', classes:['10-A','10-B'] },
  { id:2, staffCode:'T-102', name:'P. Menon', subject:'Physics', department:'Science', phone:'98xxxx202', email:'p.menon@EduConnect.local', status:'Active', classes:['9-A','9-B'] },
  { id:3, staffCode:'T-103', name:'R. Khanna', subject:'Chemistry', department:'Science', phone:'98xxxx203', email:'r.khanna@EduConnect.local', status:'Active', classes:['10-B'] },
  { id:4, staffCode:'T-104', name:'S. Das', subject:'English', department:'Languages', phone:'98xxxx204', email:'s.das@EduConnect.local', status:'On Leave', classes:['9-B'] },
  { id:5, staffCode:'T-105', name:'A. Kapoor', subject:'Computer Science', department:'Science', phone:'98xxxx205', email:'a.kapoor@EduConnect.local', status:'Active', classes:['7-C'] },
]

export async function getTeachers(): Promise<Teacher[]> { await delay(); return MOCK_TEACHERS }
