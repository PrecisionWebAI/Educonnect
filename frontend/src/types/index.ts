// ==========================================================
// EduConnect Frontend — shared domain & app types
// ==========================================================

export type Role =
  | 'DIRECTOR'
  | 'PRINCIPAL'
  | 'HOD'
  | 'CLASS_TEACHER'
  | 'SUBJECT_TEACHER'
  | 'STUDENT'
  | 'GUARDIAN'
  | 'ACCOUNTANT'
  | 'LIBRARIAN'
  | 'TRANSPORT'
  | 'ADMIN'
  | 'STAFF'

export const ROLE_LABELS: Record<Role, string> = {
  DIRECTOR: 'Director',
  PRINCIPAL: 'Principal',
  HOD: 'Head of Dept.',
  CLASS_TEACHER: 'Class Teacher',
  SUBJECT_TEACHER: 'Subject Teacher',
  STUDENT: 'Student',
  GUARDIAN: 'Parent',
  ACCOUNTANT: 'Accountant',
  LIBRARIAN: 'Librarian',
  TRANSPORT: 'Transport',
  ADMIN: 'Admin',
  STAFF: 'Staff',
}

export interface User {
  id: number
  username: string
  email: string
  fullName: string
  roles: Role[]
  department?: string
}

export interface Session {
  user: User
  accessToken: string
  refreshToken: string
}

// ---- Academic domain -------------------------------------

export interface ClassInfo {
  id: number
  name: string
  section: string
  classTeacher: string
  strength: number
}

export interface Student {
  id: number
  admissionNo: string
  name: string
  className: string
  section: string
  gender: 'Male' | 'Female'
  guardian: string
  phone: string
  email: string
  status: 'Active' | 'Inactive'
}

export interface AttendanceRecord {
  id: number
  studentName: string
  className: string
  date: string
  status: 'Present' | 'Absent' | 'Late' | 'Leave'
}

export interface MarksRow {
  subject: string
  max: number
  obtained: number
}

export interface MarksEntry {
  studentId: number
  studentName: string
  className: string
  exam: string
  rows: MarksRow[]
}

export interface Teacher {
  id: number
  staffCode: string
  name: string
  subject: string
  department: string
  phone: string
  email: string
  status: 'Active' | 'On Leave'
  classes: string[]
}

export interface TimetableSlot {
  day: string
  period: string
  className: string
  subject: string
  teacher: string
}

// ---- Dashboard / analytics -------------------------------

export interface Kpi {
  label: string
  value: string
  delta: number // +% vs last term (positive good)
  icon: string
  hint?: string
}

export interface DashboardData {
  greeting: string
  kpis: Kpi[]
  attendanceTrend: { label: string; value: number }[]
  classReport: { name: string; attending: number; marks: number }[]
  upcoming: { title: string; when: string; type: string }[]
  notices: { title: string; body: string; time: string }[]
}
