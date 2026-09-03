import type { Session, User } from '@/types'

// Mock users / auth (PAGE 01). Backend ready par ye
// file client.ts ke real login/logout se replace hogi.

const delay = (ms = 250) => new Promise((res) => setTimeout(res, ms))

export const MOCK_USERS: User[] = [
  { id:1, username:'director', email:'director@EduConnect.local', fullName:'R. Sharma', roles:['DIRECTOR'] },
  { id:2, username:'principal', email:'principal@EduConnect.local', fullName:'S. Kapoor', roles:['PRINCIPAL'] },
  { id:3, username:'hod', email:'hod@EduConnect.local', fullName:'A. Rao', roles:['HOD'], department:'Science' },
  { id:4, username:'ct', email:'class.teacher@EduConnect.local', fullName:'M. Iyer', roles:['CLASS_TEACHER'] },
  { id:5, username:'teacher', email:'teacher@EduConnect.local', fullName:'P. Menon', roles:['SUBJECT_TEACHER'] },
  { id:6, username:'student', email:'student@EduConnect.local', fullName:'Aarav Mehta', roles:['STUDENT'] },
  { id:7, username:'parent', email:'parent@EduConnect.local', fullName:'K. Mehta', roles:['GUARDIAN'] },
  { id:8, username:'accountant', email:'accounts@EduConnect.local', fullName:'N. Joshi', roles:['ACCOUNTANT'] },
  { id:9, username:'librarian', email:'library@EduConnect.local', fullName:'T. Nair', roles:['LIBRARIAN'] },
  { id:10, username:'admin', email:'admin@EduConnect.local', fullName:'System Admin', roles:['ADMIN'] },
]

export async function mockLogin(identifier: string, _password: string): Promise<Session> {
  await delay(350)
  const found = MOCK_USERS.find((u) => u.email.toLowerCase() === identifier.toLowerCase() || u.username.toLowerCase() === identifier.toLowerCase()) ?? MOCK_USERS[0]
  const user = { ...found, roles: [...found.roles] as User['roles'] }
  return { user, accessToken:'mock.access.token', refreshToken:'mock.refresh.token' }
}

export async function mockLogout(_refreshToken: string): Promise<void> {
  await delay(100)
}
