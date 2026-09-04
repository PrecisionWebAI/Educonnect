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

// ---- Role-mastered dashboard data (PAGE 02) ----

export interface ApprovalItem {
  id: number
  kind: 'Leave' | 'Fee waiver' | 'Mark dispute' | 'Paper approval'
  summary: string
  requester: string
  time: string
}

export interface OperationsBoard {
  runningClasses: number
  presentTeachers: number
  teachersTotal: number
  substitutes: number
  upcomingEvents: { title: string; when: string }[]
}

export interface ClassAttendanceStat {
  id: number
  name: string
  present: number
  total: number
}

export interface SubjectPerf {
  subject: string
  className: string
  average: number
  weakTopic: string
}

export interface QbHealthItem {
  subject: string
  mcq: number
  theory: number
  flagged: boolean
}

export interface PaperReviewItem {
  id: number
  title: string
  subject: string
  author: string
  due: string
}

export interface TodayClassItem {
  id: number
  subject: string
  className: string
  period: string
  room: string
}

export interface HomeworkStatusItem {
  className: string
  subject: string
  assigned: number
  submitted: number
}

export interface SubjectLeaveItem {
  id: number
  student: string
  type: string
  range: string
}

export interface MeetingReminderItem {
  id: number
  parent: string
  time: string
}

export interface PaperDraftItem {
  id: number
  subject: string
  title: string
  status: string
}

export interface StudentHomeworkItem {
  id: number
  title: string
  subject: string
  due: string
  done: boolean
}

export interface RecentGradeItem {
  subject: string
  score: number
  max: number
}

export interface StudentPortalData {
  name: string
  className: string
  section: string
  attendancePct: number
  avgMarks: number
  rank: number
  todaySchedule: TodayClassItem[]
  homework: StudentHomeworkItem[]
  recentGrades: RecentGradeItem[]
  leaves: { id: number; type: string; range: string; status: 'Pending' | 'Approved' | 'Rejected' }[]
  tickets: { id: number; title: string; status: 'Open' | 'In Progress' | 'Resolved' }[]
}

export interface ChildSummary {
  id: number
  name: string
  className: string
  section: string
  attendancePct: number
  avgMarks: number
  feeStatus: 'On track' | 'Due'
  pendingHw: number
}

export interface AccountantSummary {
  collectedToday: string
  collectedMonth: string
  pendingDues: number
  payrollRun: string
}

// ---- Wave 3: Teachers / Payroll / Finance / Library / Transport ----

export interface StaffMember {
  id: number
  staffCode: string
  name: string
  subject: string
  department: string
  phone: string
  email: string
  status: 'Active' | 'On Leave'
  classes: string[]
  workload: number
}

export interface PayrollEntry {
  id: number
  staffCode: string
  name: string
  basic: number
  allowances: number
  deductions: number
  net: number
  status: 'Draft' | 'Posted' | 'Paid'
}

export interface SalaryStructureRow {
  id: number
  staffCode: string
  name: string
  basic: number
  hra: number
  da: number
  special: number
  total: number
}

export interface FeeInvoice {
  id: number
  student: string
  className: string
  head: string
  amount: number
  paid: number
  due: number
  status: 'Paid' | 'Partial' | 'Due'
}

export interface ExpenseItem {
  id: number
  vendor: string
  head: string
    amount: number
  date: string
  status: 'Pending' | 'Approved'
}

// ---- Wave 4: Exams / Homework / Classroom ------------------

export interface QuestionItem {
  id: number
  subject: string
  chapter: string
  type: 'MCQ' | 'Theory' | 'Short'
  difficulty: 'Easy' | 'Medium' | 'Hard'
  text: string
  marks: number
}

export interface PaperDraftFull {
  id: number
  title: string
  subject: string
  status: 'Draft' | 'Submitted' | 'Approved'
  questions: number
  totalMarks: number
  updated: string
}

export interface ExamScheduleItem {
  id: number
  subject: string
  date: string
  time: string
  rooms: string[]
  invigilator: string
}

export interface ExamMarkingRow {
  id: number
  student: string
  subject: string
    obtained: number
  max: number
  status: 'Entered' | 'Pending'
}

export interface PaperReviewItem {
  id: number
  title: string
  subject: string
  author: string
  due: string
}


export interface HomeworkItem {
  id: number
  title: string
  subject: string
  className: string
  due: string
  assignedBy: string
  description: string
}

export interface SubmissionItem {
  id: number
  homeworkTitle: string
  student: string
  status: 'Submitted' | 'Pending' | 'Late'
  submittedAt: string
}

export interface DiaryEntry {
  id: number
  className: string
  day: string
  subject: string
  topic: string
  homework: string
  activity: string
}

export interface ClassroomItem {
  id: number
  title: string
  subject: string
  className: string
  teacher: string
  nextLesson: string
  students: number
}

export interface LessonResource {
  id: number
  type: 'Video' | 'PDF' | 'Quiz' | 'Link'
  title: string
}

export interface LessonDetail {
  id: number
  title: string
  subject: string
  className: string
  duration: string
  topics: string[]
  resources: LessonResource[]
    homework: string
}

export interface NotificationItem {
  id: number
  title: string
  body: string
  kind: 'Attendance' | 'Homework' | 'Event' | 'Booking' | 'Alert' | 'System'
  time: string
  read: boolean
  to?: 'Student' | 'Teacher' | 'Guardian' | 'Staff'
}

export interface LeaveApplicationItem {
  id: number
  student: string
  className: string
  type: 'Medical' | 'Personal' | 'OD' | 'Event' | 'Travel'
  from: string
  to: string
  reason: string
  days: number
  status: 'Pending' | 'Approved' | 'Rejected'
  submittedAt: string
}

export interface ChatConversation {
  id: number
  name: string
  group: boolean
  lastMessage: string
  time: string
  unread: number
  online?: boolean
}

export interface MeetingItem {
  id: number
  title: string
  with: string
  date: string
  time: string
  room: string
  type: 'Scheduled' | 'Pending' | 'Done'
}

export interface TicketItem {
  id: number
  subject: string
  category: 'IT' | 'Accounts' | 'Facility' | 'Academic' | 'Other'
  priority: 'Low' | 'Medium' | 'High'
  status: 'Open' | 'In Progress' | 'Resolved' | 'Closed'
  reporter: string
  assignee: string
  updated: string
}

export interface ReportCard {
  id: number
  title: string
  metric: string
  value: string
  trend: string
  tone: 'green' | 'amber' | 'red' | 'teal'
}

export interface DataQualityRow {
  id: number
  area: string
  score: number
  issue: string
  status: 'Healthy' | 'Attention' | 'Critical'
}

export interface SettingUser {
  id: number
  name: string
  email: string
  role: 'Admin' | 'Teacher' | 'Accountant' | 'Staff'
  status: 'Active' | 'Invited' | 'Disabled'
}

export interface SchoolInfo {
  id: number
  label: string
  value: string
}

export interface SecurityLog {
  id: number
  event: string
  user: string
  when: string
}

export interface CopilotAutomation {
  id: number
  title: string
  schedule: string
  lastRun: string
  active: boolean
}

export interface CopilotSuggestion {
  id: number
  prompt: string
  tag: string
}

export interface IrregularStudent {
  id: number
  name: string
  className: string
  absences: number
  pattern: string
  risk: 'High' | 'Medium' | 'Low'
}

export interface LeaveSyncRow {
  id: number
  student: string
  className: string
  from: string
  days: number
  autoMarked: string
  status: 'Synced' | 'Pending' | 'Overridden'
}

export interface ResultRow {
  id: number
  exam: string
  className: string
  passRate: number
  avgScore: number
  topper: string
}

export interface DisputeRow {
  id: number
  student: string
  exam: string
  subject: string
  reason: string
  status: 'Open' | 'Under Review' | 'Resolved'
}

export interface ClassMatrixRow {
  id: number
  className: string
  strength: number
  boys: number
  girls: number
  avgAttendance: number
}

export interface CollectionReportRow {
  id: number
  period: string
  billed: string
  collected: string
  variance: string
  mode: string
}

export interface ChatFile {
  id: number
  name: string
  sharedBy: string
  size: string
  when: string
}

export interface StaffLeaveRow {
  id: number
  name: string
  role: string
  type: string
  from: string
  days: number
  balance: number
  status: 'Pending' | 'Approved' | 'Rejected'
}

export interface EducationReportRow {
  id: number
  metric: string
  className: string
  value: string
  trend: string
}

export interface PaletteCommand {
  id: number
  label: string
  shortcut: string
  category: string
}

export interface GatewayStatus {
  id: number
  name: string
  type: string
  status: 'Connected' | 'Degraded' | 'Down'
  quota: string
}

export interface LibraryBook {
  id: number
  isbn: string
  title: string
  author: string
  category: string
  copies: number
  available: number
  overdue?: boolean
}

export interface BookIssue {
  id: number
  book: string
  student: string
  issued: string
  due: string
  status: 'Borrowed' | 'Returned' | 'Overdue'
}

export interface TransportRoute {
  id: number
  name: string
  busId: string
  driver: string
  stops: number
  students: number
  status: 'Active' | 'Idle'
}

export interface Bus {
  id: number
  name: string
  plate: string
  route: string
  capacity: number
  occupied: number
  status: 'En route' | 'Parked' | 'Service'
}
