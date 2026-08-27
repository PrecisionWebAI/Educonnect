'use client'

import { Badge, Card } from '@/components/ui'
import Icon from '@/components/ui/Icon'

// Stitch: admin_dashboard_desktop → AI insights / alerts card
const INSIGHTS: { icon: 'warning' | 'ai' | 'trending'; text: string }[] = [
  { icon: 'warning', text: 'Class 9-B attendance dipped below 85% this week.' },
  { icon: 'ai', text: 'AI suggests auto-reminder to 14 guardians of repeat absentees.' },
  { icon: 'trending', text: 'Term-1 fee collection is ahead of target by 12% — lock budget early.' },
]

export default function AiInsightsCard() {
  return (
    <Card title="AI Insights" className="dash-span-2"
      action={<Badge tone="amber">3 new</Badge>}>
      <ul className="feed">
        {INSIGHTS.map((i) => (
          <li key={i.text} className="feed-item">
            <span className="feed-ico"><Icon name={i.icon} size={16} /></span>
            <span className="feed-title" style={{ fontWeight: 400 }}>{i.text}</span>
          </li>
        ))}
      </ul>
    </Card>
  )
}