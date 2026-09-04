'use client'

import type { Student } from '@/types'
import { Badge, Modal } from '@/components/ui'

function initials(name: string) {
  return name.split(' ').map((p) => p[0]).slice(0, 2).join('').toUpperCase()
}

export default function StudentProfileModal({
  student,
  onClose,
}: {
  student: Student | null
  onClose: () => void
}) {
  return (
    <Modal open={student !== null} title="Student profile" onClose={onClose}>
      {student && (
        <>
          <div className="cell-name" style={{ marginBottom: '1rem' }}>
            <span className="cell-avatar" style={{ width: 44, height: 44, fontSize: '1rem' }}>{initials(student.name)}</span>
            <div>
              <strong style={{ fontSize: '1.05rem' }}>{student.name}</strong>
              <div style={{ color: 'var(--muted)', fontSize: '0.82rem' }}>{student.admissionNo}</div>
              <Badge tone={student.status === 'Active' ? 'green' : 'muted'}>{student.status}</Badge>
            </div>
          </div>
          <dl style={{ display: 'grid', gap: '0.45rem', color: 'var(--muted)', fontSize: '0.9rem' }}>
            <div><b style={{ color: 'var(--text)' }}>Class:</b> {student.className}-{student.section}</div>
            <div><b style={{ color: 'var(--text)' }}>Gender:</b> {student.gender}</div>
            <div><b style={{ color: 'var(--text)' }}>Guardian:</b> {student.guardian}</div>
            <div><b style={{ color: 'var(--text)' }}>Phone:</b> {student.phone}</div>
            <div><b style={{ color: 'var(--text)' }}>Email:</b> {student.email || '—'}</div>
          </dl>
        </>
      )}
    </Modal>
  )
}