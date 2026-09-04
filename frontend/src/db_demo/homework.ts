import type { HomeworkItem, SubmissionItem, DiaryEntry } from '@/types'

const delay = (ms = 250) => new Promise((res) => setTimeout(res, ms))

export async function getHomeworks(): Promise<HomeworkItem[]> {
  await delay()
  return [
    { id: 1, title: 'Trigonometry worksheet', subject: 'Mathematics', className: '10-A', due: 'Tomorrow', assignedBy: 'M. Iyer', description: 'Solve questions 1-15 from the Trigonometry chapter.' },
    { id: 2, title: 'Electricity circuit lab', subject: 'Physics', className: '10-A', due: 'Fri', assignedBy: 'P. Menon', description: 'Build a series circuit and record observations.' },
    { id: 3, title: 'Essay - My School', subject: 'English', className: '10-A', due: 'Mon', assignedBy: 'S. Das', description: 'Write a 300-word essay about your school.' },
  ]
}

export async function getSubmissions(): Promise<SubmissionItem[]> {
  await delay()
  return [
    { id: 1, homeworkTitle: 'Trigonometry worksheet', student: 'Aarav Mehta', status: 'Submitted', submittedAt: 'Yesterday' },
    { id: 2, homeworkTitle: 'Trigonometry worksheet', student: 'Diya Sharma', status: 'Submitted', submittedAt: 'Today' },
    { id: 3, homeworkTitle: 'Electricity circuit lab', student: 'Vivaan Patel', status: 'Pending', submittedAt: '-' },
    { id: 4, homeworkTitle: 'Essay - My School', student: 'Rohan Gupta', status: 'Late', submittedAt: '2 days late' },
  ]
}

export async function getDiary(): Promise<DiaryEntry[]> {
  await delay()
  return [
    { id: 1, className: '10-A', day: 'Mon', subject: 'Mathematics', topic: 'Trigonometry basics', homework: 'Worksheet 1-15', activity: 'Group quiz' },
    { id: 2, className: '10-A', day: 'Tue', subject: 'Physics', topic: 'Ohm law', homework: 'Numericals', activity: 'Lab demo' },
    { id: 3, className: '10-A', day: 'Wed', subject: 'English', topic: 'Essay writing', homework: 'Essay on school', activity: 'Peer review' },
  ]
}