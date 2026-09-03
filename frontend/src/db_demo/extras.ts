import type {
  IrregularStudent,
  LeaveSyncRow,
  ResultRow,
  DisputeRow,
  ClassMatrixRow,
  CollectionReportRow,
  ChatFile,
  StaffLeaveRow,
  EducationReportRow,
  PaletteCommand,
  GatewayStatus,
} from '@/types'

const delay = (ms = 250) => new Promise((res) => setTimeout(res, ms))

export async function getIrregularStudents(): Promise<IrregularStudent[]> {
  await delay()
  return [
    { id: 1, name: 'A. Verma', className: '8A', absences: 12, pattern: 'Mon + Fri absences', risk: 'High' },
    { id: 2, name: 'R. Singh', className: '9C', absences: 9, pattern: 'Post-lunch absences', risk: 'Medium' },
    { id: 3, name: 'S. Das', className: '7B', absences: 4, pattern: 'Scattered', risk: 'Low' },
  ]
}

export async function getLeaveSync(): Promise<LeaveSyncRow[]> {
  await delay()
  return [
    { id: 1, student: 'A. Verma', className: '8A', from: 'Aug 29', days: 2, autoMarked: 'Approved leave', status: 'Synced' },
    { id: 2, student: 'M. Rao', className: '10B', from: 'Sep 1', days: 1, autoMarked: 'Awaiting approval', status: 'Pending' },
    { id: 3, student: 'P. Gupta', className: '6A', from: 'Aug 25', days: 3, autoMarked: 'Teacher override', status: 'Overridden' },
  ]
}

export async function getResults(): Promise<ResultRow[]> {
  await delay()
  return [
    { id: 1, exam: 'Unit Test 2', className: '8A', passRate: 94, avgScore: 72, topper: 'N. Joshi' },
    { id: 2, exam: 'Unit Test 2', className: '9C', passRate: 88, avgScore: 68, topper: 'S. Mehta' },
    { id: 3, exam: 'Half Yearly', className: '10B', passRate: 91, avgScore: 75, topper: 'R. Malhotra' },
  ]
}

export async function getDisputes(): Promise<DisputeRow[]> {
  await delay()
  return [
    { id: 1, student: 'K. Shah', exam: 'Unit Test 2', subject: 'Maths', reason: 'Total mismatch on Q4', status: 'Open' },
    { id: 2, student: 'D. Pillai', exam: 'Half Yearly', subject: 'Science', reason: 'Answer not evaluated', status: 'Under Review' },
    { id: 3, student: 'V. Iyer', exam: 'Unit Test 1', subject: 'English', reason: 'Recheck requested', status: 'Resolved' },
  ]
}

export async function getClassMatrix(): Promise<ClassMatrixRow[]> {
  await delay()
  return [
    { id: 1, className: '6A', strength: 42, boys: 22, girls: 20, avgAttendance: 95 },
    { id: 2, className: '7B', strength: 40, boys: 19, girls: 21, avgAttendance: 93 },
    { id: 3, className: '8A', strength: 44, boys: 24, girls: 20, avgAttendance: 91 },
    { id: 4, className: '9C', strength: 38, boys: 20, girls: 18, avgAttendance: 89 },
    { id: 5, className: '10B', strength: 41, boys: 21, girls: 20, avgAttendance: 94 },
  ]
}

export async function getCollectionReports(): Promise<CollectionReportRow[]> {
  await delay()
  return [
    { id: 1, period: 'Today', billed: '₹1,20,000', collected: '₹98,400', variance: '-18%', mode: 'Cash 22% / Digital 78%' },
    { id: 2, period: 'This week', billed: '₹6,10,000', collected: '₹5,42,000', variance: '-11%', mode: 'Cash 19% / Digital 81%' },
    { id: 3, period: 'Term 1', billed: '₹84,00,000', collected: '₹77,60,000', variance: '-7.6%', mode: 'Cash 15% / Digital 85%' },
  ]
}

export async function getChatFiles(): Promise<ChatFile[]> {
  await delay()
  return [
    { id: 1, name: '8A-science-worksheet.pdf', sharedBy: 'P. Iyer', size: '1.2 MB', when: '2h ago' },
    { id: 2, name: 'fee-structure-2026.xlsx', sharedBy: 'M. Khan', size: '480 KB', when: 'Yesterday' },
    { id: 3, name: 'excursion-permission-slip.pdf', sharedBy: 'R. Sharma', size: '310 KB', when: 'Aug 30' },
  ]
}

export async function getStaffLeaveRequests(): Promise<StaffLeaveRow[]> {
  await delay()
  return [
    { id: 1, name: 'P. Iyer', role: 'Teacher', type: 'Casual', from: 'Sep 4', days: 1, balance: 6, status: 'Pending' },
    { id: 2, name: 'S. Bose', role: 'Staff', type: 'Sick', from: 'Aug 28', days: 3, balance: 4, status: 'Approved' },
    { id: 3, name: 'K. Nair', role: 'Teacher', type: 'Earned', from: 'Oct 10', days: 5, balance: 9, status: 'Rejected' },
  ]
}

export async function getEducationReports(): Promise<EducationReportRow[]> {
  await delay()
  return [
    { id: 1, metric: 'Pass rate', className: 'School-wide', value: '91.4%', trend: '+2.2% vs last term' },
    { id: 2, metric: 'Subject avg — Maths', className: '9C', value: '64%', trend: '-3% — needs remedial' },
    { id: 3, metric: 'Top-performing subject', className: '10B', value: 'Science (82%)', trend: 'Stable' },
    { id: 4, metric: 'Students at risk', className: '8A', value: '3', trend: '+1 vs last month' },
  ]
}

export async function getPaletteCommands(): Promise<PaletteCommand[]> {
  await delay()
  return [
    { id: 1, label: 'Mark attendance', shortcut: 'G A', category: 'Navigate' },
    { id: 2, label: 'Raise a ticket', shortcut: 'G T', category: 'Navigate' },
    { id: 3, label: 'Collect fee', shortcut: 'G F', category: 'Navigate' },
    { id: 4, label: 'Summarise today', shortcut: '⌘ ⇧ S', category: 'AI' },
    { id: 5, label: 'Draft fee reminder', shortcut: '⌘ ⇧ F', category: 'AI' },
  ]
}

export async function getGateways(): Promise<GatewayStatus[]> {
  await delay()
  return [
    { id: 1, name: 'WhatsApp Business', type: 'Messaging', status: 'Connected', quota: '4,210 / 10,000 today' },
    { id: 2, name: 'SMS Gateway', type: 'Messaging', status: 'Connected', quota: '1,050 / 5,000 today' },
    { id: 3, name: 'Razorpay', type: 'Payments', status: 'Degraded', quota: 'UPI slow — monitoring' },
    { id: 4, name: 'Email (SMTP)', type: 'Messaging', status: 'Connected', quota: '820 / 8,000 today' },
  ]
}