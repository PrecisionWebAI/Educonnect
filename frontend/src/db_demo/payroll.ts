import type { PayrollEntry, SalaryStructureRow } from '@/types'

const delay = (ms = 250) => new Promise((res) => setTimeout(res, ms))

export async function getSalaryStructure(): Promise<SalaryStructureRow[]> {
  await delay()
  return [
    { id: 1, staffCode: 'T-101', name: 'P. Menon', basic: 42000, hra: 16800, da: 8400, special: 6000, total: 73200 },
    { id: 2, staffCode: 'T-102', name: 'M. Iyer', basic: 40000, hra: 16000, da: 8000, special: 5000, total: 69000 },
    { id: 3, staffCode: 'T-104', name: 'S. Kapoor', basic: 45000, hra: 18000, da: 9000, special: 7000, total: 79000 },
    { id: 4, staffCode: 'T-105', name: 'R. Verma', basic: 38000, hra: 15200, da: 7600, special: 4500, total: 65300 },
    { id: 5, staffCode: 'T-106', name: 'K. Nair', basic: 52000, hra: 20800, da: 10400, special: 8000, total: 91200 },
    { id: 6, staffCode: 'T-107', name: 'D. Singh', basic: 35000, hra: 14000, da: 7000, special: 4000, total: 60000 },
  ]
}

export async function getPayrollEntry(): Promise<PayrollEntry[]> {
  await delay()
  return [
    { id: 1, staffCode: 'T-101', name: 'P. Menon', basic: 42000, allowances: 31200, deductions: 5200, net: 68000, status: 'Paid' },
    { id: 2, staffCode: 'T-102', name: 'M. Iyer', basic: 40000, allowances: 29000, deductions: 4800, net: 64200, status: 'Posted' },
    { id: 3, staffCode: 'T-104', name: 'S. Kapoor', basic: 45000, allowances: 34000, deductions: 5500, net: 73500, status: 'Draft' },
    { id: 4, staffCode: 'T-106', name: 'K. Nair', basic: 52000, allowances: 39200, deductions: 6400, net: 84800, status: 'Paid' },
  ]
}