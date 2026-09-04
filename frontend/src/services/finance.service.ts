import { api } from "@/lib/api/client";
import type {
    CollectionReportRow,
    ExpenseItem,
    FeeInvoice,
    PayrollEntry,
    SalaryStructureRow,
} from "@/types";

export async function getFeeInvoices(): Promise<FeeInvoice[]> {
    return api.get<FeeInvoice[]>("/finance/invoices");
}

export async function getExpenses(): Promise<ExpenseItem[]> {
    return api.get<ExpenseItem[]>("/finance/expenses");
}

export async function getCollectionReports(): Promise<CollectionReportRow[]> {
    return api.get<CollectionReportRow[]>("/finance/collection-reports");
}

export async function getSalaryStructure(): Promise<SalaryStructureRow[]> {
    return api.get<SalaryStructureRow[]>("/finance/salary-structure");
}

export async function getPayrollEntry(): Promise<PayrollEntry[]> {
    return api.get<PayrollEntry[]>("/finance/payroll");
}
