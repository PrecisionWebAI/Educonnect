import type {
  QuestionItem,
  PaperDraftFull,
  ExamScheduleItem,
  ExamMarkingRow,
  PaperReviewItem,
} from '@/types'

const delay = (ms = 250) => new Promise((res) => setTimeout(res, ms))

export async function getQuestionBank(): Promise<QuestionItem[]> {
  await delay()
  return [
    { id: 1, subject: 'Physics', chapter: 'Electricity', type: 'MCQ', difficulty: 'Easy', text: 'Which unit measures electric current?', marks: 1 },
    { id: 2, subject: 'Physics', chapter: 'Electricity', type: 'Theory', difficulty: 'Medium', text: 'Explain Ohm law with a circuit diagram.', marks: 5 },
    { id: 3, subject: 'Physics', chapter: 'Motion', type: 'Short', difficulty: 'Hard', text: 'Differentiate distance and displacement.', marks: 3 },
    { id: 4, subject: 'Chemistry', chapter: 'Organic', type: 'MCQ', difficulty: 'Easy', text: 'Which is a hydrocarbon?', marks: 1 },
    { id: 5, subject: 'Chemistry', chapter: 'Organic', type: 'Theory', difficulty: 'Hard', text: 'Explain aromaticity with examples.', marks: 5 },
    { id: 6, subject: 'Mathematics', chapter: 'Trigonometry', type: 'Short', difficulty: 'Medium', text: 'Prove the identity sin^2 + cos^2 = 1.', marks: 3 },
  ]
}

export async function getPaperDraftsFull(): Promise<PaperDraftFull[]> {
  await delay()
  return [
    { id: 1, title: 'Term-2 Physics Unit Test', subject: 'Physics', status: 'Approved', questions: 20, totalMarks: 40, updated: '2 days ago' },
    { id: 2, title: 'Chemistry Mid-Term Paper', subject: 'Chemistry', status: 'Submitted', questions: 25, totalMarks: 50, updated: '1 day ago' },
    { id: 3, title: 'Mathematics Weekly Quiz', subject: 'Mathematics', status: 'Draft', questions: 10, totalMarks: 20, updated: 'Just now' },
  ]
}

export async function getExamSchedule(): Promise<ExamScheduleItem[]> {
  await delay()
  return [
    { id: 1, subject: 'Mathematics', date: '22 Aug 2026', time: '9:00–12:00', rooms: ['Hall A', 'Rm-201'], invigilator: 'M. Iyer' },
    { id: 2, subject: 'Physics', date: '24 Aug 2026', time: '9:00–12:00', rooms: ['Lab-3', 'Hall B'], invigilator: 'P. Menon' },
    { id: 3, subject: 'Chemistry', date: '26 Aug 2026', time: '9:00–12:00', rooms: ['Hall A'], invigilator: 'R. Khanna' },
  ]
}

export async function getExamMarkings(): Promise<ExamMarkingRow[]> {
  await delay()
  return [
    { id: 1, student: 'Aarav Mehta', subject: 'Physics', obtained: 42, max: 50, status: 'Entered' },
    { id: 2, student: 'Diya Sharma', subject: 'Physics', obtained: 46, max: 50, status: 'Entered' },
    { id: 3, student: 'Vivaan Patel', subject: 'Physics', obtained: 0, max: 50, status: 'Pending' },
  ]
}

export async function getExamPaperReviews(): Promise<PaperReviewItem[]> {
  await delay()
  return [
    { id: 1, title: 'Term-2 Physics draft', subject: 'Physics', author: 'P. Menon', due: 'Today' },
    { id: 2, title: 'Chemistry MCQs', subject: 'Chemistry', author: 'R. Khanna', due: 'Tomorrow' },
  ]
}