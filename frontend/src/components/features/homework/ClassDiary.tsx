'use client'
import { Table, Badge, type BadgeTone } from '@/components/ui'
import type { DiaryEntry } from '@/types'

export default function ClassDiary({ rows }: { rows: DiaryEntry[] }) {
  const cols = [
    { key: 'day', header: 'Day', render: (r: DiaryEntry) => <Badge tone="accent">{r.day}</Badge> },
    { key: 'subject', header: 'Subject' },
    { key: 'topic', header: 'Topic' },
    { key: 'activity', header: 'Activity' },
    { key: 'homework', header: 'Homework' },
  ]
  return <Table columns={cols} rows={rows} rowKey={(r) => r.id} empty="No diary entries." />
}