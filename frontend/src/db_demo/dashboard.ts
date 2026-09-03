import type {
  AccountantSummary,
  ApprovalItem,
  ChildSummary,
  ClassAttendanceStat,
  DashboardData,
  HomeworkStatusItem,
  MeetingReminderItem,
  OperationsBoard,
  PaperDraftItem,
  PaperReviewItem,
  QbHealthItem,
  StudentPortalData,
  SubjectLeaveItem,
  SubjectPerf,
  TodayClassItem,
} from '@/types'

const delay = (ms = 250) => new Promise((res) => setTimeout(res, ms))

const KPI_BASE = [
  { label: 'Total Students', value: '1,284', delta: 4.2, icon: 'students' },
  { label: 'Attendance Today', value: '93.1%', delta: 1.8, icon: 'attendance' },
  { label: 'Avg. Marks (Term 1)', value: '82.4%', delta: 2.6, icon: 'marks' },
  { label: 'Fees Collected', value: '48.2L', delta: 12.4, icon: 'fees' },
  { label: 'Pending Approvals', value: '17', delta: -5.0, icon: 'approvals' },
  { label: 'Open Tickets', value: '23', delta: 3.0, icon: 'tickets' },
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
      { title: 'Parent Teacher Meeting', when: '28 Aug 2026', type: 'Meeting' },
      { title: 'Sports Day rehearsals', when: '2 Sep 2026', type: 'Event' },
    ],
    notices: [
      { title: 'Fee payment window opens', body: 'Term 2 fees can be paid online from next week.', time: '2h ago' },
      { title: 'Mid-term marks entry due', body: 'All subject teachers to complete grade entry by Friday.', time: '5h ago' },
      { title: 'Transport route D time change', body: 'Route D return timing moves to 4:30 PM.', time: 'Yesterday' },
    ],
  }
}

export async function getApprovals(): Promise<ApprovalItem[]> {
  await delay()
  return [
    { id: 1, kind: 'Leave', summary: 'Diya Sharma - Sick leave', requester: 'Diya', time: '1h ago' },
    { id: 2, kind: 'Fee waiver', summary: 'Sibling discount - S. Verma family', requester: 'S. Verma', time: '3h ago' },
    { id: 3, kind: 'Mark dispute', summary: 'Physics Term-1 recheck (74 to 79)', requester: 'Arjun', time: '5h ago' },
    { id: 4, kind: 'Paper approval', summary: 'Term-2 Physics paper draft', requester: 'P. Menon', time: 'Yesterday' },
  ]
}

export async function getOperationsBoard(): Promise<OperationsBoard> {
  await delay()
  return {
    runningClasses: 18,
    presentTeachers: 21,
    teachersTotal: 24,
    substitutes: 3,
    upcomingEvents: [
      { title: 'PTM - Class 10', when: 'Today 4 PM' },
      { title: 'Science Exhibit', when: 'Fri 9 AM' },
    ],
  }
}

export async function getClassAttendance(): Promise<ClassAttendanceStat[]> {
  await delay()
  return [
    { id: 1, name: '10-A', present: 40, total: 42 },
    { id: 2, name: '10-B', present: 38, total: 40 },
    { id: 3, name: '9-A', present: 41, total: 45 },
    { id: 4, name: '9-B', present: 33, total: 38 },
    { id: 5, name: '7-C', present: 33, total: 35 },
  ]
}

export async function getSubjectPerf(): Promise<SubjectPerf[]> {
  await delay()
  return [
    { subject: 'Mathematics', className: '10-A', average: 88, weakTopic: 'Trigonometry' },
    { subject: 'Physics', className: '10-A', average: 82, weakTopic: 'Electricity' },
    { subject: 'Chemistry', className: '10-B', average: 84, weakTopic: 'Organic' },
    { subject: 'English', className: '9-B', average: 79, weakTopic: 'Grammar' },
  ]
}

export async function getQbHealth(): Promise<QbHealthItem[]> {
  await delay()
  return [
    { subject: 'Mathematics', mcq: 45, theory: 12, flagged: false },
    { subject: 'Physics', mcq: 30, theory: 8, flagged: true },
    { subject: 'Chemistry', mcq: 22, theory: 6, flagged: false },
  ]
}

export async function getTodayClasses(): Promise<TodayClassItem[]> {
  await delay()
  return [
    { id: 1, subject: 'Mathematics', className: '10-A', period: 'P1', room: 'Rm-201' },
    { id: 2, subject: 'Physics', className: '10-A', period: 'P2', room: 'Lab-3' },
    { id: 3, subject: 'Chemistry', className: '10-B', period: 'P4', room: 'Lab-1' },
  ]
}

export async function getHomeworkStatus(): Promise<HomeworkStatusItem[]> {
  await delay()
  return [
    { className: '10-A', subject: 'Mathematics', assigned: 42, submitted: 38 },
    { className: '10-A', subject: 'Physics', assigned: 42, submitted: 34 },
    { className: '10-B', subject: 'Chemistry', assigned: 40, submitted: 34 },
  ]
}

export async function getSubjectLeaves(): Promise<SubjectLeaveItem[]> {
  await delay()
  return [
    { id: 1, student: 'Vivaan Patel', type: 'Medical', range: '19-21 Aug' },
    { id: 2, student: 'Saanvi Gupta', type: 'OD', range: '20 Aug' },
  ]
}

export async function getMeetingReminders(): Promise<MeetingReminderItem[]> {
  await delay()
  return [
    { id: 1, parent: 'H. Patel', time: 'Today 3:30 PM' },
    { id: 2, parent: 'V. Singh', time: 'Fri 11 AM' },
  ]
}

export async function getPaperDrafts(): Promise<PaperDraftItem[]> {
  await delay()
  return [
    { id: 1, subject: 'Physics', title: 'Term-2 Unit Test', status: 'Draft' },
    { id: 2, subject: 'Physics', title: 'MCQ Bank - Current', status: 'Pending edit' },
  ]
}

export async function getStudentPortal(): Promise<StudentPortalData> {
  await delay()
  return {
    name: 'Aarav Mehta',
    className: '10',
    section: 'A',
    attendancePct: 94,
    avgMarks: 88,
    rank: 4,
    todaySchedule: [
      { id: 1, subject: 'Mathematics', className: '10-A', period: 'P1', room: 'Rm-201' },
      { id: 2, subject: 'Physics', className: '10-A', period: 'P2', room: 'Lab-3' },
      { id: 3, subject: 'English', className: '10-A', period: 'P5', room: 'Rm-105' },
    ],
    homework: [
      { id: 1, title: 'Trigonometry worksheet', subject: 'Mathematics', due: 'Today', done: false },
      { id: 2, title: 'Electricity circuit lab', subject: 'Physics', due: 'Tomorrow', done: false },
      { id: 3, title: 'Essay - My School', subject: 'English', due: 'Completed', done: true },
    ],
    recentGrades: [
      { subject: 'Mathematics', score: 88, max: 100 },
      { subject: 'Physics', score: 82, max: 100 },
      { subject: 'English', score: 79, max: 100 },
      { subject: 'Chemistry', score: 91, max: 100 },
    ],
    leaves: [
      { id: 1, type: 'Medical', range: '19-21 Aug', status: 'Approved' },
      { id: 2, type: 'OD', range: '2 Aug', status: 'Rejected' },
      { id: 3, type: 'Medical', range: '26 Aug', status: 'Pending' },
    ],
    tickets: [
      { id: 1, title: 'Marks dispute - Physics', status: 'In Progress' },
      { id: 2, title: 'Library fine query', status: 'Resolved' },
    ],
  }
}

export async function getParentData(): Promise<ChildSummary[]> {
  await delay()
  return [
    { id: 1, name: 'Aarav Mehta', className: '10', section: 'A', attendancePct: 94, avgMarks: 88, feeStatus: 'On track', pendingHw: 2 },
    { id: 2, name: 'Diya Sharma', className: '10', section: 'A', attendancePct: 88, avgMarks: 81, feeStatus: 'Due', pendingHw: 1 },
  ]
}

export async function getAccountantSummary(): Promise<AccountantSummary> {
  await delay()
  return {
    collectedToday: '46,200',
    collectedMonth: '48.2L',
    pendingDues: 23,
    payrollRun: 'Processing (86%)',
  }
}

export async function getPaperReviews(): Promise<PaperReviewItem[]> {
  await delay()
  return [
    { id: 1, title: 'Term-2 Physics draft', subject: 'Physics', author: 'P. Menon', due: 'Today' },
    { id: 2, title: 'Chemistry MCQs', subject: 'Chemistry', author: 'R. Khanna', due: 'Tomorrow' },
  ]
}