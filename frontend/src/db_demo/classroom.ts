import type { ClassroomItem, LessonDetail } from '@/types'

const delay = (ms = 250) => new Promise((res) => setTimeout(res, ms))

export async function getClassrooms(): Promise<ClassroomItem[]> {
  await delay()
  return [
    { id: 1, title: 'Physics - Class 10A', subject: 'Physics', className: '10-A', teacher: 'P. Menon', nextLesson: 'Electricity - Ohm law', students: 42 },
    { id: 2, title: 'Mathematics - Class 10A', subject: 'Mathematics', className: '10-A', teacher: 'M. Iyer', nextLesson: 'Trigonometry - Ratios', students: 42 },
    { id: 3, title: 'English - Class 9B', subject: 'English', className: '9-B', teacher: 'S. Das', nextLesson: 'Essay writing', students: 38 },
  ]
}

export async function getLessonDetail(): Promise<LessonDetail> {
  await delay()
  return {
    id: 1,
    title: 'Ohm Law and Circuits',
    subject: 'Physics',
    className: '10-A',
    duration: '45 min',
    topics: ['Current and voltage', 'Resistance', 'Ohm law', 'Series circuits'],
    resources: [
      { id: 1, type: 'Video', title: 'Introduction to circuits' },
      { id: 2, type: 'PDF', title: 'Ohm law notes' },
      { id: 3, type: 'Quiz', title: 'Quick check - 5 questions' },
    ],
    homework: 'Solve numericals 1-10 from the worksheet.',
  }
}