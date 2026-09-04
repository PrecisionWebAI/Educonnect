'use client'

// Quick demo role access chips (replaces biometrics until backend).
const ACCOUNTS = [
  { label: 'Director', identifier: 'director' },
  { label: 'Principal', identifier: 'principal' },
  { label: 'HOD', identifier: 'hod' },
  { label: 'Teacher', identifier: 'ct' },
  { label: 'Student', identifier: 'student' },
  { label: 'Parent', identifier: 'parent' },
]

export default function DemoRoleChips({
  disabled,
  onPick,
}: {
  disabled: boolean
  onPick: (identifier: string) => void
}) {
  return (
    <div className="demo-grid">
      {ACCOUNTS.map((d) => (
        <button
          key={d.identifier}
          type="button"
          className="demo-chip"
          disabled={disabled}
          onClick={() => onPick(d.identifier)}
        >
          {d.label}
        </button>
      ))}
    </div>
  )
}