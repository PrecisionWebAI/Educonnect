'use client'
import { Table, Badge, type BadgeTone } from '@/components/ui'
import type { QuestionItem } from '@/types'

const typeTone: Record<QuestionItem['type'], BadgeTone> = { MCQ: 'teal', Short: 'violet', Theory: 'accent' }
const diffTone: Record<QuestionItem['difficulty'], BadgeTone> = { Easy: 'green', Medium: 'amber', Hard: 'red' }

export default function QuestionBank({ rows }: { rows: QuestionItem[] }) {
  const columns = [
    { key: 'text', header: 'Question', render: (r: QuestionItem) => <span style={{ fontSize: '0.88rem' }}>{r.text}</span> },
    { key: 'subject', header: 'Subject' },
    { key: 'chapter', header: 'Chapter' },
    { key: 'type', header: 'Type', render: (r: QuestionItem) => <Badge tone={typeTone[r.type]}>{r.type}</Badge> },
    { key: 'difficulty', header: 'Difficulty', render: (r: QuestionItem) => <Badge tone={diffTone[r.difficulty]}>{r.difficulty}</Badge> },
    { key: 'marks', header: 'Marks' },
  ]
  return <Table columns={columns} rows={rows} rowKey={(r) => r.id} empty="No questions match the filters." />
}