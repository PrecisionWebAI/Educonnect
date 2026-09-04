'use client'

import { Badge, Card } from '@/components/ui'
import Icon from '@/components/ui/Icon'

// Stitch: admin_dashboard_desktop → "Recent Activity" feed
const ACTIVITY: { icon: 'check' | 'ai' | 'wallet' | 'edit'; text: string; time: string }[] = [
  { icon: 'check', text: 'Attendance synced · Class 10-A', time: '8 min ago' },
  { icon: 'ai', text: 'Auto-verified by EduConnect AI · Fee receipt #1042', time: '22 min ago' },
  { icon: 'wallet', text: 'Bank reconciliation completed · ₹1.2L matched', time: '1 hr ago' },
  { icon: 'edit', text: 'Term-1 marks entry approved · Mathematics', time: '2 hrs ago' },
]

export default function RecentActivity() {
  return (
    <Card title="Recent Activity" className="dash-span-2"
      action={<Badge tone="green">Live</Badge>}>
      <ul className="feed">
        {ACTIVITY.map((a) => (
          <li key={a.text} className="feed-item">
            <span className="feed-ico"><Icon name={a.icon} size={16} /></span>
            <div className="feed-body">
              <span className="feed-title">{a.text}</span>
              <span className="feed-time">{a.time}</span>
            </div>
          </li>
        ))}
      </ul>
    </Card>
  )
}