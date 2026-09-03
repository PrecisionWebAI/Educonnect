'use client'
import { useState } from 'react'
import { Button, Select, Card } from '@/components/ui'
import { useToast } from '@/components/ui/toast'

const chapters = ['Electricity', 'Motion', 'Organic', 'Trigonometry', 'Force']
const difficulties = ['Easy', 'Medium', 'Hard']

export default function AiPaperGenerator() {
  const [subject, setSubject] = useState('Physics')
  const [chapter, setChapter] = useState('Electricity')
  const [difficulty, setDifficulty] = useState('Medium')
  const [qCount, setQCount] = useState(10)
  const [generated, setGenerated] = useState<string[]>([])
  const { push } = useToast()

  function handleGenerate() {
    setGenerated([
      `Q1. Fundamental question on ${chapter} (${difficulty}).`,
      `Q2. Explain key concept in ${subject} - ${chapter}.`,
      `Q3. Numeric problem on ${chapter} (${difficulty}).`,
      `Q4. Short answer on ${chapter}.`,
      `Q5. MCQ related to ${subject}.`,
    ])
    push('success', `Paper generated with ${qCount} questions`)
  }

  return (
    <div style={{ display: 'grid', gap: '1rem', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))' }}>
      <Card title="Paper Configuration">
        <div className="form-grid">
          <Select label="Subject" value={subject} onChange={(e) => setSubject(e.target.value)}>
            {['Physics', 'Chemistry', 'Mathematics', 'English'].map((s) => <option key={s}>{s}</option>)}
          </Select>
          <Select label="Chapter" value={chapter} onChange={(e) => setChapter(e.target.value)}>
            {chapters.map((c) => <option key={c}>{c}</option>)}
          </Select>
          <Select label="Difficulty" value={difficulty} onChange={(e) => setDifficulty(e.target.value)}>
            {difficulties.map((d) => <option key={d}>{d}</option>)}
          </Select>
          <Select label="Questions" value={String(qCount)} onChange={(e) => setQCount(Number(e.target.value))}>
            {[5, 10, 15, 20].map((n) => <option key={n} value={n}>{n} questions</option>)}
          </Select>
        </div>
        <div className="modal-actions">
          <Button variant="primary" onClick={handleGenerate}>Generate with AI</Button>
        </div>
      </Card>

      <Card title="Generated Paper Preview" action={<Button variant="ghost" size="sm">Add to Bank</Button>}>
        {generated.length === 0 ? (
          <p style={{ color: 'var(--muted)' }}>Configure and generate to see a preview.</p>
        ) : (
          <ol style={{ paddingLeft: '1.2rem', gap: '0.4rem', display: 'flex', flexDirection: 'column' }}>
            {generated.map((q, i) => <li key={i} style={{ fontSize: '0.88rem' }}>{q}</li>)}
          </ol>
        )}
      </Card>
    </div>
  )
}