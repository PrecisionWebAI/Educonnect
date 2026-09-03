import type { TicketItem } from '@/types'
const delay = (ms = 250) => new Promise((res) => setTimeout(res, ms))
export async function getTickets(): Promise<TicketItem[]> {
  await delay()
  return [
    { id:  1, subject: 'Printer not working in Rm-201', category: 'IT', priority: 'High', status: 'In Progress', reporter: 'P. Menon', assignee: 'Tech Desk', updated: '1h' },
    { id:  2, subject: 'Fee receipt not generated', category: 'Accounts', priority: 'Medium', status: 'Open', reporter: 'N. Joshi', assignee: 'Finance', updated: '3h' },
    { id:  3, subject: 'AC cooling issue in Hall A', category: 'Facility', priority: 'Medium', status: 'In Progress', reporter: 'S. Kapoor', assignee: 'Maintenance', updated: 'Yesterday' },
  ]
}
