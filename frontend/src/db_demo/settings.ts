import type { SettingUser, SchoolInfo, SecurityLog } from '@/types'

const delay = (ms = 250) => new Promise((res) => setTimeout(res, ms))

export async function getSettingUsers(): Promise<SettingUser[]> {
  await delay()
  return [
    { id: 1, name: 'R. Sharma', email: 'r.sharma@school.edu', role: 'Admin', status: 'Active' },
    { id: 2, name: 'P. Iyer', email: 'p.iyer@school.edu', role: 'Teacher', status: 'Active' },
    { id: 3, name: 'M. Khan', email: 'm.khan@school.edu', role: 'Accountant', status: 'Active' },
    { id: 4, name: 'S. Bose', email: 's.bose@school.edu', role: 'Staff', status: 'Invited' },
    { id: 5, name: 'K. Nair', email: 'k.nair@school.edu', role: 'Staff', status: 'Disabled' },
  ]
}

export async function getSchoolInfo(): Promise<SchoolInfo[]> {
  await delay()
  return [
    { id: 1, label: 'School name', value: 'Educonnect Public School' },
    { id: 2, label: 'Affiliation', value: 'CBSE — 1130456' },
    { id: 3, label: 'Academic session', value: '2026-27' },
    { id: 4, label: 'Address', value: 'Sector 12, Pune, Maharashtra' },
    { id: 5, label: 'Contact', value: '+91 98200 11223' },
  ]
}

export async function getSecurityLogs(): Promise<SecurityLog[]> {
  await delay()
  return [
    { id: 1, event: 'Password changed', user: 'r.sharma@school.edu', when: 'Today, 09:12' },
    { id: 2, event: 'New device sign-in', user: 'p.iyer@school.edu', when: 'Yesterday, 17:40' },
    { id: 3, event: 'Role updated to Accountant', user: 'm.khan@school.edu', when: 'Aug 28' },
    { id: 4, event: 'Failed login attempts (5)', user: 'k.nair@school.edu', when: 'Aug 26' },
  ]
}