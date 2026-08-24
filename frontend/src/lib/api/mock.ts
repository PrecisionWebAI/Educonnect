import type {
  AttendanceRecord,
  ClassInfo,
  DashboardData,
  Kpi,
  MarksEntry,
  Session,
  Student,
  Teacher,
  TimetableSlot,
  User,
} from '@/types'

// ==========================================================
// Mock data layer (UI-first build — no backend required).
// Every function returns a Promise so components can call it
// exactly like the real API. When the backend is ready, point
// these at client.ts and delete this file's bodies.
// ==========================================================

const delay = (ms = 250) => new Promise((res) => setTimeout(res, ms))

// ---- Mock users / auth ------------------------------------

const MOCK_USERS: User[] = [
  { id: 1, username: 'director', email: 'director@EduConnect.local', fullName: 'R. Sharma', roles: ['DIRECTOR'] },
  { id: 2, username: 'principal', email: 'principal@EduConnect.local', fullName: 'S. Kapoor', roles: ['PRINCIPAL'] },
  { id: 3, username: 'hod', email: 'hod@EduConnect.local', fullName: 'A. Rao', roles: ['HOD'], department: 'Science' },
  { id: 4, username: 'ct', email: 'class.teacher@EduConnect.local', fullName: 'M. Iyer', roles: ['CLASS_TEACHER'] },
  { id: 5, username: 'teacher', email: 'teacher@EduConnect.local', fullName: 'P. Menon', roles: ['SUBJECT_TEACHER'] },
  { id: 6, username: 'student', email: 'student@EduConnect.local', fullName: 'Aarav Mehta', roles: ['STUDENT'] },
  { id: 7, username: 'parent', email: 'parent@EduConnect.local', fullName: 'K. Mehta', roles: ['GUARDIAN'] },
  { id: 8, username: 'accountant', email: 'accounts@EduConnect.local', fullName: 'N. Joshi', roles: ['ACCOUNTANT'] },
  { id: 9, username: 'librarian', email: 'library@EduConnect.local', fullName: 'T. Nair', roles: ['LIBRARIAN'] },
  { id: 10, username: 'admin', email: 'admin@EduConnect.local', fullName: 'System Admin', roles: ['ADMIN'] },
]

export async function mockLogin(
  identifier: string,
  _password: string,
): Promise<Session> {
  await delay(350)
  const found =
    MOCK_USERS.find(
      (u) => u.email.toLowerCase() === identifier.toLowerCase() || u.username.toLowerCase() === identifier.toLowerCase(),
    ) ?? MOCK_USERS[0]
  const user = { ...found, roles: [...found.roles] as User['roles'] }
  return {
    user,
    accessToken: 'mock.access.token',
    refreshToken: 'mock.refresh.token',
  }
}

export async function mockLogout(_refreshToken: string): Promise<void> {
  await delay(100)
}

// ---- Students -------------------------------------------------------

export const MOCK_STUDENTS: Student[] = [
  { id: 1, admissionNo: 'EV-2026-001', name: 'Aarav Mehta', className: '10', section: 'A', gender: 'Male', guardian: 'K. Mehta', phone: '98xxxx001', email: 'aarav@school.edu', status: 'Active' },
  { id: 2, admissionNo: 'EV-2026-002', name: 'Diya Sharma', className: '10', section: 'A', gender: 'Female', guardian: 'R. Sharma', phone: '98xxxx002', email: 'diya@school.edu', status: 'Active' },
  { id: 3, admissionNo: 'EV-2026-003', name: 'Vivaan Patel', className: '10', section: 'A', gender: 'Male', guardian: 'H. Patel', phone: '98xxxx003', email: 'vivaan@school.edu', status: 'Active' },
  { id: 4, admissionNo: 'EV-2026-004', name: 'Anaya Singh', className: '10', section: 'A', gender: 'Female', guardian: 'V. Singh', phone: '98xxxx004', email: 'anaya@school.edu', status: 'Active' },
  { id: 5, admissionNo: 'EV-2026-005', name: 'Arjun Verma', className: '9', section: 'B', gender: 'Male', guardian: 'S. Verma', phone: '98xxxx005', email: 'arjun@school.edu', status: 'Inactive' },
  { id: 6, admissionNo: 'EV-2026-006', name: 'Isha Reddy', className: '9', section: 'B', gender: 'Female', guardian: 'M. Reddy', phone: '98xxxx006', email: 'isha@school.edu', status: 'Active' },
  { id: 7, admissionNo: 'EV-2026-007', name: 'Saanvi Gupta', className: '7', section: 'C', gender: 'Female', guardian: 'A. Gupta', phone: '98xxxx007', email: 'saanvi@school.edu', status: 'Active' },
  { id: 8, admissionNo: 'EV-2026-008', name: 'Ishaan Kumar', className: '7', section: 'C', gender: 'Male', guardian: 'D. Kumar', phone: '98xxxx008', email: 'ishaan@school.edu', status: 'Active' },
]

export const MOCK_CLASSES: ClassInfo[] = [
  { id: 1, name: '10', section: 'A', classTeacher: 'M. Iyer', strength: 42 },
  { id: 2, name: '10', section: 'B', classTeacher: 'R. Khanna', strength: 40 },
  { id: 3, name: '9', section: 'A', classTeacher: 'P. Menon', strength: 45 },
  { id: 4, name: '9', section: 'B', classTeacher: 'S. Das', strength: 38 },
  { id: 5, name: '7', section: 'C', classTeacher: 'A. Rao', strength: 35 },
]

export async function getStudents(): Promise<Student[]> {
  await delay()
  return MOCK_STUDENTS
}

export async function getClasses(): Promise<ClassInfo[]> {
  await delay()
  return MOCK_CLASSES
}

// ---- Attendance ----------------------------------------------------

export const MOCK_ATTENDANCE: AttendanceRecord[] = [
  { id: 1, studentName: 'Aarav Mehta', className: '10-A', date: '2026-08-19', status: 'Present' },
  { id: 2, studentName: 'Diya Sharma', className: '10-A', date: '2026-08-19', status: 'Present' },
  { id: 3, studentName: 'Kabir Patel', className: '10-A', date: '2026-08-19', status: 'Absent' },
  { id: 4, studentName: 'Ananya Singh', className: '10-A', date: '2026-08-19', status: 'Late' },
  { id: 5, studentName: 'Vivaan Patel', className: '10-A', date: '2026-08-19', status: 'Present' },
  { id: 6, studentName: 'Rohan Verma', className: '9-B', date: '2026-08-19', status: 'Absent' },
  { id: 7, studentName: 'Isha Reddy', className: '9-B', date: '2026-08-19', status: 'Present' },
  { id: 8, studentName: 'Saanvi Gupta', className: '7-C', date: '2026-08-19', status: 'Present' },
]

export async function getAttendance(): Promise<AttendanceRecord[]> {
  await delay()
  return MOCK_ATTENDANCE
}

// ---- Marks ----------------------------------------------------------

export const MOCK_MARKS: MarksEntry[] = [
  {
    studentId: 1, studentName: 'Aarav Mehta', className: '10-A', exam: 'Term 1',
    rows: [
      { subject: 'Mathematics', max: 100, obtained: 88 },
      { subject: 'Science', max: 100, obtained: 82 },
      { subject: 'English', max: 100, obtained: 79 },
    ],
  },
  {
    studentId: 2, studentName: 'Diya Sharma', className: '10-A', exam: 'Term 1',
    rows: [
      { subject: 'Mathematics', max: 100, obtained: 91 },
      { subject: 'Science', max: 100, obtained: 95 },
      { subject: 'English', max: 100, obtained: 86 },
    ],
  },
  {
    studentId: 4, studentName: 'Ananya Singh', className: '10-A', exam: 'Term 1',
    rows: [
      { subject: 'Mathematics', max: 100, obtained: 74 },
      { subject: 'Science', max: 100, obtained: 70 },
      { subject: 'English', max: 100, obtained: 90 },
    ],
  },
]

export async function getMarks(): Promise<MarksEntry[]> {
  await delay()
  return MOCK_MARKS
}

// ---- Teachers -------------------------------------------------------

export const MOCK_TEACHERS: Teacher[] = [
  { id: 1, staffCode: 'T-101', name: 'M. Iyer', subject: 'Mathematics', department: 'Science', phone: '98xxxx201', email: 'm.iyer@EduConnect.local', status: 'Active', classes: ['10-A', '10-B'] },
  { id: 2, staffCode: 'T-102', name: 'P. Menon', subject: 'Physics', department: 'Science', phone: '98xxxx202', email: 'p.menon@EduConnect.local', status: 'Active', classes: ['9-A', '9-B'] },
  { id: 3, staffCode: 'T-103', name: 'R. Khanna', subject: 'Chemistry', department: 'Science', phone: '98xxxx203', email: 'r.khanna@EduConnect.local', status: 'Active', classes: ['10-B'] },
  { id: 4, staffCode: 'T-104', name: 'S. Das', subject: 'English', department: 'Languages', phone: '98xxxx204', email: 's.das@EduConnect.local', status: 'On Leave', classes: ['9-B'] },
  { id: 5, staffCode: 'T-105', name: 'A. Kapoor', subject: 'Computer Science', department: 'Science', phone: '98xxxx205', email: 'a.kapoor@EduConnect.local', status: 'Active', classes: ['7-C'] },
]

export async function getTeachers(): Promise<Teacher[]> {
  await delay()
  return MOCK_TEACHERS
}

// ---- Timetable ------------------------------------------------------

export const MOCK_TIMETABLE: TimetableSlot[] = [
  { day: 'Mon', period: 'P1', className: '10-A', subject: 'Mathematics', teacher: 'M. Iyer' },
  { day: 'Mon', period: 'P2', className: '10-A', subject: 'Physics', teacher: 'P. Menon' },
  { day: 'Tue', period: 'P1', className: '10-A', subject: 'Chemistry', teacher: 'R. Khanna' },
  { day: 'Wed', period: 'P3', className: '10-A', subject: 'English', teacher: 'S. Das' },
]

export async function getTimetable(): Promise<TimetableSlot[]> {
  await delay()
  return MOCK_TIMETABLE
}

// ---- Dashboard ------------------------------------------------------

const KPI_BASE: Kpi[] = [
  { label: 'Total Students', value: '1,284', delta: 4.2, icon: '🎓' },
  { label: 'Attendance Today', value: '93.1%', delta: 1.8, icon: '✅' },
  { label: 'Avg. Marks (Term 1)', value: '82.4%', delta: 2.6, icon: '📊' },
  { label: 'Fees Collected', value: '₹48.2L', delta: 12.4, icon: '💰' },
  { label: 'Pending Approvals', value: '17', delta: -5.0, icon: '📝' },
  { label: 'Open Tickets', value: '23', delta: 3.0, icon: '🎫' },
]

export async function getDashboard(): Promise<DashboardData> {
  await delay()
  return {
    greeting: 'Good morning',
    kpis: KPI_BASE,
    attendanceTrend: [
      { label: 'Mon', value: 92 },
      { label: 'Tue', value: 95 },
      { label: 'Wed', value: 94 },
      { label: 'Thu', value: 98 },
      { label: 'Fri', value: 96 },
      { label: 'Sat', value: 98 },
    ],
    classReport: [
      { name: '10-A', attending: 97, marks: 88 },
      { name: '10-B', attending: 94, marks: 84 },
      { name: '9-A', attending: 96, marks: 81 },
      { name: '9-B', attending: 91, marks: 79 },
      { name: '7-C', attending: 95, marks: 86 },
    ],
    upcoming: [
      { title: 'Term 1 Exams begin', when: '22 Aug 2026', type: 'Exam' },
      { title: 'Parent–Teacher Meeting', when: '28 Aug 2026', type: 'Meeting' },
      { title: 'Sports Day — rehearsals', when: '2 Sep 2026', type: 'Event' },
    ],
    notices: [
      { title: 'Fee payment window opens', body: 'Term 2 fees can be paid online from next week.', time: '2h ago' },
      { title: 'Mid-term marks entry due', body: 'All subject teachers to complete grade entry by Friday.', time: '5h ago' },
      { title: 'Transport route D time change', body: 'Route D return timing moves to 4:30 PM.', time: 'Yesterday' },
    ],
  }
}
