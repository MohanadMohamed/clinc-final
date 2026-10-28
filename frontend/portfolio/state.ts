import type { Patient } from "../src/lib/patients";
import type { Appointment } from "../src/lib/appointments";
import type { Visit } from "../src/lib/visits";
import type { Fee, Invoice, Payment } from "../src/lib/billing";
import { cairoDate, localCandidates } from "../src/lib/cairo";
export type Perspective = "doctor" | "receptionist";
export type Revision = {
    revision: number;
    actor_id: string;
    event: string;
    neurological_note: string;
    psychiatric_note: string;
    follow_up_plan: string;
    occurred_at: string;
};
const id = (n: number) => `00000000-0000-4000-8000-${String(n).padStart(12, "0")}`;
const now = () => new Date().toISOString();
const slot = (clock: string) => localCandidates(cairoDate(), clock)[0];
function seed() {
    const timestamp = now();
    const patients: Patient[] = Array.from({ length: 12 }, (_, i) => ({ id: id(i + 1), full_name: `مريض اصطناعي ${String(i + 1).padStart(2, "0")}`, phone: `0000000${String(i + 1).padStart(4, "0")}`, birth_date: i % 3 === 0 ? null : "1990-01-01", active: true, created_at: timestamp, updated_at: timestamp, archived_at: null }));
    const appointments: Appointment[] = ["09:00", "10:00", "11:00", "14:00"].map((clock, i) => ({ id: id(101 + i), patient_id: id(i + 1), kind: i % 2 ? "follow_up" : "first_visit", status: "scheduled", start_at: slot(clock), end_at: slot(`${clock.slice(0, 2)}:30`), created_at: timestamp, updated_at: timestamp }));
    const visits: Visit[] = [{ id: id(201), patient_id: id(1), appointment_id: id(101), status: "finalized", revision: 1, created_at: timestamp, updated_at: timestamp, finalized_at: timestamp, neurological_note: "ملاحظة اصطناعية للتعريف بواجهة التحرير فقط. لا تمثل حالة طبية.", psychiatric_note: "نص تجريبي مصطنع بالكامل؛ لا توجد بيانات شخص حقيقي.", follow_up_plan: "خطة متابعة توضيحية فقط، بلا توصية طبية." }, { id: id(202), patient_id: id(5), appointment_id: null, status: "draft", revision: 1, created_at: timestamp, updated_at: timestamp, finalized_at: null, neurological_note: "مسودة اصطناعية قابلة للتعديل في هذه الجولة.", psychiatric_note: "", follow_up_plan: "" }];
    const fees: Fee[] = [{ kind: "first_visit", amount_minor: 30000, occurred_at: timestamp }, { kind: "follow_up", amount_minor: 15000, occurred_at: timestamp }];
    const invoices: Invoice[] = [{ id: id(301), patient_id: id(1), appointment_id: null, visit_id: null, kind: "first_visit", status: "issued", currency: "EGP", base_minor: 30000, adjustment_minor: 0, total_minor: 30000, paid_minor: 10000, balance_minor: 20000, created_at: timestamp }, { id: id(302), patient_id: id(2), appointment_id: null, visit_id: null, kind: "follow_up", status: "draft", currency: "EGP", base_minor: 15000, adjustment_minor: 0, total_minor: 15000, paid_minor: 0, balance_minor: 15000, created_at: timestamp }];
    const payments: Payment[] = [{ id: id(401), invoice_id: id(301), amount_minor: 10000, currency: "EGP", occurred_at: timestamp, reversed: false }];
    const histories: Record<string, Revision[]> = Object.fromEntries(visits.map(v => [v.id, [{ revision: 1, actor_id: id(901), event: "created", neurological_note: v.neurological_note, psychiatric_note: v.psychiatric_note, follow_up_plan: v.follow_up_plan, occurred_at: timestamp }]]));
    return { patients, appointments, visits, fees, invoices, payments, histories };
}
export let data = seed();
export let perspective: Perspective | null = null;
let version = 0;
const listeners = new Set<() => void>();
export const changed = () => { version++; listeners.forEach(fn => fn()); };
export const subscribe = (fn: () => void) => { listeners.add(fn); return () => listeners.delete(fn); };
export const snapshot = () => version;
export function choosePerspective(value: Perspective | null) { perspective = value; changed(); }
export function resetDemo() { data = seed(); invoiceKeys.clear(); paymentKeys.clear(); changed(); }
export const invoiceKeys = new Map<string, {
    patient: string;
    kind: string;
    id: string;
}>();
export const paymentKeys = new Map<string, {
    invoice: string;
    amount: number;
    id: string;
}>();
export const newId = () => crypto.randomUUID();
export const timestamp = now;
export const copy = <T,>(value: T): T => structuredClone(value);
