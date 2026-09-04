import type { LibraryBook, BookIssue } from '@/types'

const delay = (ms = 250) => new Promise((res) => setTimeout(res, ms))

export async function getLibraryBooks(): Promise<LibraryBook[]> {
  await delay()
  return [
    { id: 1, isbn: '978-0141036144', title: '1984', author: 'George Orwell', category: 'Fiction', copies: 12, available: 8 },
    { id: 2, isbn: '978-0061120084', title: 'To Kill a Mockingbird', author: 'Harper Lee', category: 'Fiction', copies: 10, available: 4 },
    { id: 3, isbn: '978-8126521195', title: 'Wings of Fire', author: 'A.P.J. Abdul Kalam', category: 'Biography', copies: 15, available: 12 },
    { id: 4, isbn: '978-8172234980', title: 'Discovery of India', author: 'Jawaharlal Nehru', category: 'History', copies: 6, available: 2 },
    { id: 5, isbn: '978-0140283332', title: 'A Brief History of Time', author: 'Stephen Hawking', category: 'Science', copies: 8, available: 5 },
  ]
}

export async function getBookIssues(): Promise<BookIssue[]> {
  await delay()
  return [
    { id: 1, book: '1984', student: 'Aarav Mehta', issued: '2026-08-20', due: '2026-09-03', status: 'Overdue' },
    { id: 2, book: 'Wings of Fire', student: 'Ishita Rao', issued: '2026-08-27', due: '2026-09-10', status: 'Borrowed' },
    { id: 3, book: 'Discovery of India', student: 'Ananya Das', issued: '2026-08-28', due: '2026-09-11', status: 'Borrowed' },
    { id: 4, book: '1984', student: 'Rohan Gupta', issued: '2026-08-15', due: '2026-08-29', status: 'Overdue' },
  ]
}