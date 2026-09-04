import type { MarksEntry } from '@/types'

const delay = (ms = 250) => new Promise((res) => setTimeout(res, ms))

export const MOCK_MARKS: MarksEntry[] = [
  { studentId: 1, studentName: 'Aarav Mehta', className: '10-A', exam: 'Term 1', rows: [
      { subject: 'Mathematics', max: 100, obtained:   88 },
      { subject: 'Science', max: 100, obtained:    82 },
      { subject: 'English', max:  100, obtained:   79 }
    ] },
  { studentId:  2, studentName: 'Diya Sharma', className: '10-A', exam: 'Term 1', rows: [
      { subject: 'Mathematics', max:  100, obtained:91 },
      { subject: 'Science', max:100, obtained:95 },
      { subject: 'English', max:100, obtained:86 }
    ] },
  { studentId:4, studentName: 'Ananya Singh', className: '10-A', exam: 'Term 1', rows: [
      { subject: 'Mathematics', max:100, obtained:74 },
      { subject: 'Science', max:100, obtained:70 },
      { subject: 'English', max:100, obtained:90 }
    ] },
]

export async function getMarks(): Promise<MarksEntry[]> {
  await delay()
  return MOCK_MARKS
}