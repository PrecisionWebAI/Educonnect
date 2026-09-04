import type { ReportCard, DataQualityRow } from '@/types'

const delay = (ms = 250) => new Promise((res) => setTimeout(res, ms))

export async function getReportCards(): Promise<ReportCard[]> {
  await delay()
  return [
    { id: 1, title: 'Fee Collection', metric: 'Collected vs Billed', value: '92.4%', trend: '+3.1% vs last term', tone: 'green' },
    { id: 2, title: 'Attendance Health', metric: 'Avg daily attendance', value: '94.1%', trend: '-0.8% vs last month', tone: 'amber' },
    { id: 3, title: 'Exam Performance', metric: 'Average score', value: '71.8%', trend: '+2.4% vs last exam', tone: 'teal' },
    { id: 4, title: 'Fee Defaulter Rate', metric: 'Overdue accounts', value: '7.6%', trend: '+1.2% vs last term', tone: 'red' },
  ]
}

export async function getDataQuality(): Promise<DataQualityRow[]> {
  await delay()
  return [
    { id: 1, area: 'Student records', score: 98, issue: '3 profiles missing guardian phone', status: 'Healthy' },
    { id: 2, area: 'Fee ledger', score: 91, issue: '12 receipts pending reconciliation', status: 'Attention' },
    { id: 3, area: 'Attendance logs', score: 96, issue: '2 backdated entries flagged', status: 'Healthy' },
    { id: 4, area: 'Exam marks entry', score: 62, issue: '8A-B term marks incomplete', status: 'Critical' },
  ]
}