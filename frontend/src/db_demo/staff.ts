import type { StaffMember } from '@/types'

const delay = (ms = 250) => new Promise((res) => setTimeout(res, ms))

export interface WorkloadMatrixRow { staff: string; subject: string; classes: string[]; periods: number; utilisation: number }
export interface StaffLeaveItem { id:number; staff:string; from:string; to:string; reason:string; substitute:string; status:'Approved'|'Pending'|'Rejected' }
export interface StaffPerformance { id:number; staff:string; rating:number; reviews:number; trend:'up'|'flat'|'down'; score:number }

export async function getStaff(): Promise<StaffMember[]> {
  await delay()
  return [
    { id:1, staffCode:'T-101', name:'P. Menon', subject:'Physics', department:'Science', phone:'+91 98xxxxxx01', email:'p.menon@edu.local', status:'Active', classes:['10-A','10-B','9-A'], workload:18 },
    { id:2, staffCode:'T-102', name:'M. Iyer', subject:'Mathematics', department:'Science', phone:'+91 98xxxxxx02', email:'m.iyer@edu.local', status:'Active', classes:['10-A','11-A'], workload:16 },
    { id:3, staffCode:'T-103', name:'A. Rao', subject:'Chemistry', department:'Science', phone:'+91 98xxxxxx03', email:'a.rao@edu.local', status:'On Leave', classes:['11-B'], workload:12 },
    { id:4, staffCode:'T-104', name:'S. Kapoor', subject:'English', department:'Languages', phone:'+91 98xxxxxx04', email:'s.kapoor@edu.local', status:'Active', classes:['9-A','9-B','10-A'], workload:20 },
    { id:5, staffCode:'T-105', name:'R. Verma', subject:'History', department:'Social Studies', phone:'+91 98xxxxxx05', email:'r.verma@edu.local', status:'Active', classes:['8-A','8-B'], workload:14 },
    { id:6, staffCode:'T-106', name:'K. Nair', subject:'Computer Science', department:'Technology', phone:'+91 98xxxxxx06', email:'k.nair@edu.local', status:'Active', classes:['12-A','11-A'], workload:15 },
    { id:7, staffCode:'T-107', name:'D. Singh', subject:'Physical Education', department:'Sports', phone:'+91 98xxxxxx07', email:'d.singh@edu.local', status:'Active', classes:['All'], workload:22 },
    { id:8, staffCode:'T-108', name:'L. Bose', subject:'Biology', department:'Science', phone:'+91 98xxxxxx08', email:'l.bose@edu.local', status:'On Leave', classes:['10-B','12-A'], workload:13 },
  ]
}

export async function getWorkloadMatrix(): Promise<WorkloadMatrixRow[]> {
  await delay()
  return [
    { staff:'P. Menon', subject:'Physics', classes:['10-A','10-B','9-A'], periods:18, utilisation:82 },
    { staff:'M. Iyer', subject:'Mathematics', classes:['10-A','11-A'], periods:16, utilisation:74 },
    { staff:'S. Kapoor', subject:'English', classes:['9-A','9-B','10-A'], periods:20, utilisation:91 },
    { staff:'R. Verma', subject:'History', classes:['8-A','8-B'], periods:14, utilisation:64 },
    { staff:'K. Nair', subject:'Computer Science', classes:['12-A','11-A'], periods:15, utilisation:70 },
    { staff:'D. Singh', subject:'Physical Education', classes:['All'], periods:22, utilisation:95 },
  ]
}

export async function getStaffLeaves(): Promise<StaffLeaveItem[]> {
  await delay()
  return [
    { id:1, staff:'A. Rao', from:'2026-09-05', to:'2026-09-09', reason:'Medical', substitute:'T. Nair', status:'Approved' },
    { id:2, staff:'L. Bose', from:'2026-09-08', to:'2026-09-10', reason:'Personal', substitute:'Unassigned', status:'Pending' },
    { id:3, staff:'S. Kapoor', from:'2026-09-12', to:'2026-09-12', reason:'Seminar', substitute:'M. Iyer', status:'Pending' },
  ]
}

export async function getStaffPerformance(): Promise<StaffPerformance[]> {
  await delay()
  return [
    { id:1, staff:'P. Menon', rating:4.6, reviews:12, trend:'up', score:88 },
    { id:2, staff:'M. Iyer', rating:4.4, reviews:10, trend:'up', score:84 },
    { id:3, staff:'S. Kapoor', rating:4.8, reviews:15, trend:'up', score:92 },
    { id:4, staff:'R. Verma', rating:4.1, reviews:8, trend:'flat', score:76 },
    { id:5, staff:'K. Nair', rating:4.3, reviews:9, trend:'flat', score:80 },
    { id:6, staff:'D. Singh', rating:4.7, reviews:11, trend:'up', score:90 },
  ]
}
