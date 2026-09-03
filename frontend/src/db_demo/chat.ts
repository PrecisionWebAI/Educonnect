import type { ChatConversation } from '@/types'
const delay = (ms = 250) => new Promise((res) => setTimeout(res, ms))
export async function getChatConversations(): Promise<ChatConversation[]> {
  await delay()
  return [
    { id:  1, name: 'Aarav Mehta', group:false, lastMessage: 'Can you share the Physics notes?', time: '10m', unread:  2, online:true },
    { id:  2, name: 'Class 10-A', group:true, lastMessage: 'P. Menon: Homework due tomorrow', time: '1h', unread:  5 },
    { id:  3, name: 'Diya Sharma', group:false, lastMessage: 'Thanks for the schedule!', time: '2h', unread:  0, online:false },
  ]
}
