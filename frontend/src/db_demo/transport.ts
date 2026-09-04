import type { TransportRoute, Bus } from '@/types'

const delay = (ms = 250) => new Promise((res) => setTimeout(res, ms))

export async function getTransportRoutes(): Promise<TransportRoute[]> {
  await delay()
  return [
    { id: 1, name: 'Route A North', busId: 'B-01', driver: 'R. Sharma', stops: 8, students: 45, status: 'Active' },
    { id: 2, name: 'Route B East', busId: 'B-02', driver: 'S. Verma', stops: 6, students: 38, status: 'Active' },
    { id: 3, name: 'Route C South', busId: 'B-03', driver: 'M. Khan', stops: 7, students: 40, status: 'Idle' },
    { id: 4, name: 'Route D West', busId: 'B-04', driver: 'A. Singh', stops: 5, students: 32, status: 'Active' },
  ]
}

export async function getBuses(): Promise<Bus[]> {
  await delay()
  return [
    { id: 1, name: 'B-01', plate: 'MH-01-AB-1234', route: 'Route A North', capacity: 50, occupied: 45, status: 'En route' },
    { id: 2, name: 'B-02', plate: 'MH-01-CD-5678', route: 'Route B East', capacity: 45, occupied: 38, status: 'En route' },
    { id: 3, name: 'B-03', plate: 'MH-01-EF-9012', route: 'Route C South', capacity: 50, occupied: 20, status: 'Parked' },
    { id: 4, name: 'B-04', plate: 'MH-01-GH-3456', route: 'Route D West', capacity: 40, occupied: 32, status: 'Service' },
  ]
}