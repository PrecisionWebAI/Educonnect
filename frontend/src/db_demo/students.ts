import type { Student, ClassInfo } from '@/types'

const delay = (ms = 250) => new Promise((res) => setTimeout(res, ms))

export const MOCK_STUDENTS: Student[] = [
  { id:1, admissionNo:'EV-2026-001', name:'Aarav Mehta', className:'10', section:'A', gender:'Male', guardian:'K. Mehta', phone:'98xxxx001', email:'aarav@school.edu', status:'Active' },
  { id:2, admissionNo:'EV-2026-002', name:'Diya Sharma', className:'10', section:'A', gender:'Female', guardian:'R. Sharma', phone:'98xxxx002', email:'diya@school.edu', status:'Active' },
  { id:3, admissionNo:'EV-2026-003', name:'Vivaan Patel', className:'10', section:'A', gender:'Male', guardian:'H. Patel', phone:'98xxxx003', email:'vivaan@school.edu', status:'Active' },
  { id:4, admissionNo:'EV-2026-004', name:'Ananya Singh', className:'10', section:'A', gender:'Female', guardian:'V. Singh', phone:'98xxxx004', email:'ananya@school.edu', status:'Active' },
  { id:5, admissionNo:'EV-2026-005', name:'Arjun Verma', className:'9', section:'B', gender:'Male', guardian:'S. Verma', phone:'98xxxx005', email:'arjun@school.edu', status:'Inactive' },
  { id:6, admissionNo:'EV-2026-006', name:'Isha Reddy', className:'9', section:'B', gender:'Female', guardian:'M. Reddy', phone:'98xxxx006', email:'isha@school.edu', status:'Active' },
  { id:7, admissionNo:'EV-2026-007', name:'Saanvi Gupta', className:'7', section:'C', gender:'Female', guardian:'A. Gupta', phone:'98xxxx007', email:'saanvi@school.edu', status:'Active' },
  { id:8, admissionNo:'EV-2026-008', name:'Ishaan Kumar', className:'7', section:'C', gender:'Male', guardian:'D. Kumar', phone:'98xxxx008', email:'ishaan@school.edu', status:'Active' },
]

export const MOCK_CLASSES: ClassInfo[] = [
  { id:1, name:'10', section:'A', classTeacher:'M. Iyer', strength:42 },
  { id:2, name:'10', section:'B', classTeacher:'R. Khanna', strength:40 },
  { id:3, name:'9', section:'A', classTeacher:'P. Menon', strength:45 },
  { id:4, name:'9', section:'B', classTeacher:'S. Das', strength:38 },
  { id:5, name:'7', section:'C', classTeacher:'A. Rao', strength:35 },
]

export async function getStudents(): Promise<Student[]> { await delay(); return MOCK_STUDENTS }
export async function getClasses(): Promise<ClassInfo[]> { await delay(); return MOCK_CLASSES }
