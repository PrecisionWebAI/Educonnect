import type { MeetingItem } from '@/types'
const delay = (ms = 250) => new Promise((res) => setTimeout(res, ms))
export async function getMeetings(): Promise<MeetingItem[]> {
  await delay()
  return [
    { id:  1, title: 'PTM - Class 10', with: 'H. Patel', date: '2026/08/28', time: '4 PM', room: 'Hall A', type: 'Scheduled' },
    { id:  2, title: 'Science Exhibit Planning', with: 'Staff Team', date: '2026/09/04', time: '11 AM', room: 'Lab-2', type: 'Pending' },
    { id:  3, title: 'Board Review', with: 'Principal', date: '2026/09/10', time: '2 PM', room: 'Office', type: 'Done' },
  ]
}
