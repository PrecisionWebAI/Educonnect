import type { FeeInvoice, ExpenseItem } from '@/types'

const delay = (ms = 250) => new Promise((res) => setTimeout(res, ms))

export async function getFeeInvoices(): Promise<FeeInvoice[]> {
  await delay()
  return [
    { id: 1, student: 'Aarav Mehta', className: '10-A', head: 'Tuition Fee', amount: 45000, paid: 45000, due: 0, status: 'Paid' },
    { id: 2, student: 'Ishita Rao', className: '9-B', head: 'Tuition Fee', amount: 42000, paid: 25000, due: 17000, status: 'Partial' },
    { id: 3, student: 'Kabir Singh', className: '11-A', head: 'Tuition Fee', amount: 50000, paid: 0, due: 50000, status: 'Due' },
    { id: 4, student: 'Ananya Das', className: '10-B', head: 'Transport Fee', amount: 12000, paid: 12000, due: 0, status: 'Paid' },
    { id: 5, student: 'Rohan Gupta', className: '8-A', head: 'Tuition Fee', amount: 38000, paid: 20000, due: 18000, status: 'Partial' },
    { id: 6, student: 'Meera Nair', className: '12-A', head: 'Caution Deposit', amount: 20000, paid: 0, due: 20000, status: 'Due' },
  ]
}

export async function getExpenses(): Promise<ExpenseItem[]> {
  await delay()
  return [
    { id: 1, vendor: 'ABC Stationery', head: 'Office Supplies', amount: 12000, date: '2026-08-28', status: 'Approved' },
    { id: 2, vendor: 'Solar Solutions', head: 'Utilities', amount: 45000, date: '2026-08-30', status: 'Pending' },
    { id: 3, vendor: 'TechMart', head: 'IT Equipment', amount: 80000, date: '2026-09-01', status: 'Pending' },
    { id: 4, vendor: 'Garden Nursery', head: 'Maintenance', amount: 15000, date: '2026-08-25', status: 'Approved' },
  ]
}