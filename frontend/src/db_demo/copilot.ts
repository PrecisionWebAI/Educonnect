import type { CopilotAutomation, CopilotSuggestion } from '@/types'

const delay = (ms = 250) => new Promise((res) => setTimeout(res, ms))

export async function getAutomations(): Promise<CopilotAutomation[]> {
  await delay()
  return [
    { id: 1, title: 'Daily attendance digest to class teachers', schedule: 'Every day 08:00', lastRun: 'Today, 08:00', active: true },
    { id: 2, title: 'Fee reminder for overdue accounts', schedule: 'Every Monday 10:00', lastRun: 'Aug 31', active: true },
    { id: 3, title: 'Weekly homework submission summary', schedule: 'Every Friday 16:00', lastRun: 'Aug 29', active: true },
    { id: 4, title: 'Low-stock alert for library', schedule: 'Monthly, 1st', lastRun: 'Aug 1', active: false },
  ]
}

export async function getCopilotSuggestions(): Promise<CopilotSuggestion[]> {
  await delay()
  return [
    { id: 1, prompt: 'Summarise today\'s attendance gaps by class', tag: 'Attendance' },
    { id: 2, prompt: 'Draft a fee reminder for defaulters', tag: 'Finance' },
    { id: 3, prompt: 'Generate a revision worksheet for 8A Science', tag: 'Academics' },
    { id: 4, prompt: 'Which students need counselling this week?', tag: 'Wellbeing' },
  ]
}