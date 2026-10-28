/** In-memory portfolio adapter. No network, credentials, backend or persistent storage. */
import type { Patient, PatientInput } from "../src/lib/patients";
import type { Appointment, TimeInput } from "../src/lib/appointments";
import type { Visit, VisitSummary } from "../src/lib/visits";
import type { Invoice, Payment, Fee } from "../src/lib/billing";
import { cairoDate } from "../src/lib/cairo";
import { data, perspective, changed, copy, newId, timestamp, invoiceKeys, paymentKeys } from "./state";
export type { Patient, PatientInput, Appointment, TimeInput, Visit, VisitSummary, Invoice, Payment, Fee };
const pageOf = <T,>(items: T[], page = 1, page_size = 10) => copy({ items: items.slice((page - 1) * page_size, page * page_size), total: items.length, page, page_size });
const need = <T,>(value: T | undefined): T => { if (!value)
    throw new Error("السجل الاصطناعي غير موجود"); return value; };
const doctor = () => { if (perspective !== "doctor")
    throw new Error("هذه الشاشة متاحة في منظور الطبيب فقط؛ ليست مصادقة حقيقية."); };
const patient = (id: string) => need(data.patients.find(p => p.id === id));
const active = (id: string) => { const p = patient(id); if (!p.active)
    throw new Error("السجل الاصطناعي مؤرشف"); return p; };
export async function listPatients(search: string, page: number) { const term = search.toLocaleLowerCase(); return pageOf(data.patients.filter(p => p.active && (!term || p.full_name.toLocaleLowerCase().includes(term) || p.phone.includes(term))), page); }
export async function getPatient(id: string) { return copy(patient(id)); }
export async function createPatient(input: PatientInput) { const duplicate = data.patients.some(p => p.active && p.full_name === input.full_name && p.phone === input.phone); if (duplicate && !input.confirm_duplicate)
    throw new Error("قد يكون المريض مسجلاً بالفعل. راجع التشابه."); const { confirm_duplicate: _, ...fields } = input; const p: Patient = { ...fields, id: newId(), active: true, created_at: timestamp(), updated_at: timestamp(), archived_at: null }; data.patients.unshift(p); changed(); return copy(p); }
export async function updatePatient(id: string, input: Partial<PatientInput>) { const p = active(id); Object.assign(p, { ...(input.full_name !== undefined ? { full_name: input.full_name } : {}), ...(input.phone !== undefined ? { phone: input.phone } : {}), ...(input.birth_date !== undefined ? { birth_date: input.birth_date } : {}) }, { updated_at: timestamp() }); changed(); return copy(p); }
export async function archivePatient(id: string) { const p = active(id); if (data.appointments.some(a => a.patient_id === id && a.status === "scheduled"))
    throw new Error("ألغِ المواعيد المجدولة قبل أرشفة هذا السجل الاصطناعي."); p.active = false; p.archived_at = timestamp(); p.updated_at = timestamp(); changed(); return copy(p); }
export class AppointmentError extends Error {
    constructor(public status: number, message: string) { super(message); }
}
export async function getAppointments(start: string, end: string, status: "scheduled" | "cancelled" | "all", page: number) { return pageOf(data.appointments.filter(a => a.start_at < end && a.end_at > start && (status === "all" || a.status === status)).sort((a, b) => a.start_at.localeCompare(b.start_at)), page, 100); }
function validateSlot(input: TimeInput, except?: string) { const start = Date.parse(input.start_at), end = Date.parse(input.end_at); if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start)
    throw new AppointmentError(422, "اختر بداية ونهاية صالحتين."); if (data.appointments.some(a => a.id !== except && a.status === "scheduled" && Date.parse(a.start_at) < end && Date.parse(a.end_at) > start))
    throw new AppointmentError(409, "الموعد محجوز بالفعل. تم تحديث القائمة، اختر وقتاً آخر."); }
export async function createAppointment(input: TimeInput & {
    patient_id: string;
    kind: Appointment["kind"];
}) { active(input.patient_id); validateSlot(input); const a: Appointment = { ...input, id: newId(), status: "scheduled", created_at: timestamp(), updated_at: timestamp() }; data.appointments.push(a); changed(); return copy(a); }
export async function rescheduleAppointment(id: string, input: TimeInput) { const a = need(data.appointments.find(x => x.id === id)); if (a.status !== "scheduled")
    throw new AppointmentError(400, "الموعد ملغى"); validateSlot(input, id); Object.assign(a, input, { updated_at: timestamp() }); changed(); return copy(a); }
export async function cancelAppointment(id: string) { const a = need(data.appointments.find(x => x.id === id)); a.status = "cancelled"; a.updated_at = timestamp(); changed(); return copy(a); }
export async function listVisits(patientId?: string, page = 1) { doctor(); return pageOf(data.visits.filter(v => !patientId || v.patient_id === patientId), page); }
export async function getVisit(id: string) { doctor(); return copy(need(data.visits.find(v => v.id === id))); }
export async function getVisitHistory(id: string) { doctor(); return copy({ revisions: need(data.histories[id]), addenda: [] as {
        id: string;
        actor_id: string;
        body: string;
        occurred_at: string;
    }[] }); }
function revision(v: Visit, event: string) { data.histories[v.id] ??= []; data.histories[v.id].push({ revision: v.revision, actor_id: "synthetic-doctor", event, neurological_note: v.neurological_note, psychiatric_note: v.psychiatric_note, follow_up_plan: v.follow_up_plan, occurred_at: timestamp() }); }
export async function createVisit(patient_id: string, appointment_id?: string) { doctor(); active(patient_id); if (appointment_id && data.visits.some(v => v.appointment_id === appointment_id))
    throw new Error("توجد زيارة اصطناعية لهذا الموعد بالفعل"); const v: Visit = { id: newId(), patient_id, appointment_id: appointment_id ?? null, status: "draft", revision: 1, created_at: timestamp(), updated_at: timestamp(), finalized_at: null, neurological_note: "", psychiatric_note: "", follow_up_plan: "" }; data.visits.unshift(v); revision(v, "created"); changed(); return copy(v); }
function editableVisit(id: string, expected: number) { doctor(); const v = need(data.visits.find(x => x.id === id)); if (v.status !== "draft" || v.revision !== expected)
    throw new Error("تغيّر السجل الاصطناعي أو تم اعتماده"); return v; }
export async function saveVisit(id: string, expected: number, notes: {
    neurological_note: string;
    psychiatric_note: string;
    follow_up_plan: string;
}) { const v = editableVisit(id, expected); Object.assign(v, notes, { revision: v.revision + 1, updated_at: timestamp() }); revision(v, "updated"); changed(); return copy(v); }
export async function finalizeVisit(id: string, expected: number) { const v = editableVisit(id, expected); v.status = "finalized"; v.revision++; v.finalized_at = timestamp(); v.updated_at = timestamp(); revision(v, "finalized"); changed(); return copy(v); }
export function minorToText(value: number) { const sign = value < 0 ? "−" : ""; const n = Math.abs(value); return `${sign}${Math.floor(n / 100).toLocaleString("ar-EG")}٫${String(n % 100).padStart(2, "0")} ج.م`; }
export function textToMinor(value: string) { if (!/^\d+(?:\.\d{1,2})?$/.test(value.trim()))
    throw new Error("أدخل مبلغاً صحيحاً حتى منزلتين عشريتين"); const [whole, cents = ""] = value.trim().split("."); const n = Number(whole) * 100 + Number(cents.padEnd(2, "0")); if (!Number.isSafeInteger(n) || n <= 0 || n > 2000000000)
    throw new Error("المبلغ خارج النطاق المسموح"); return n; }
export async function getFees() { return copy(data.fees); }
export async function setFee(kind: Fee["kind"], amount_minor: number, reason: string) { doctor(); if (reason.trim().length < 3 || !Number.isSafeInteger(amount_minor) || amount_minor <= 0)
    throw new Error("تحقق من الرسم وسبب التغيير"); const f = need(data.fees.find(x => x.kind === kind)); f.amount_minor = amount_minor; f.occurred_at = timestamp(); changed(); return copy(f); }
export async function listInvoices(page = 1) { return pageOf(data.invoices, page); }
export async function getInvoice(id: string) { return copy(need(data.invoices.find(i => i.id === id))); }
export async function getPayments(id: string) { return copy(data.payments.filter(p => p.invoice_id === id)); }
export async function createInvoice(input: {
    idempotency_key: string;
    patient_id: string;
    kind: Fee["kind"];
}) { const prior = invoiceKeys.get(input.idempotency_key); if (prior) {
    if (prior.patient !== input.patient_id || prior.kind !== input.kind)
        throw new Error("تعارض في طلب الفاتورة الاصطناعي");
    return getInvoice(prior.id);
} active(input.patient_id); const fee = need(data.fees.find(f => f.kind === input.kind)); const i: Invoice = { id: newId(), patient_id: input.patient_id, kind: input.kind, appointment_id: null, visit_id: null, status: "draft", currency: "EGP", base_minor: fee.amount_minor, adjustment_minor: 0, total_minor: fee.amount_minor, paid_minor: 0, balance_minor: fee.amount_minor, created_at: timestamp() }; data.invoices.unshift(i); invoiceKeys.set(input.idempotency_key, { patient: input.patient_id, kind: input.kind, id: i.id }); changed(); return copy(i); }
export async function issueInvoice(id: string) { const i = need(data.invoices.find(x => x.id === id)); i.status = "issued"; changed(); return copy(i); }
export async function recordPayment(id: string, amount_minor: number, key: string) { const prior = paymentKeys.get(key); if (prior) {
    if (prior.invoice !== id || prior.amount !== amount_minor)
        throw new Error("تعارض في الدفعة الاصطناعية");
    return copy(need(data.payments.find(p => p.id === prior.id)));
} const i = need(data.invoices.find(x => x.id === id)); if (i.status !== "issued" || !Number.isSafeInteger(amount_minor) || amount_minor <= 0 || amount_minor > i.balance_minor)
    throw new Error("تحقق من الرصيد وحالة الفاتورة"); const p: Payment = { id: newId(), invoice_id: id, amount_minor, currency: "EGP", occurred_at: timestamp(), reversed: false }; data.payments.push(p); i.paid_minor += amount_minor; i.balance_minor = i.total_minor - i.paid_minor; paymentKeys.set(key, { invoice: id, amount: amount_minor, id: p.id }); changed(); return copy(p); }
export async function getDaily(day: string) { const total = data.payments.filter(p => !p.reversed && cairoDate(new Date(p.occurred_at)) === day).reduce((sum, p) => sum + p.amount_minor, 0); return { day, currency: "EGP" as const, received_minor: total, reversed_minor: 0, net_minor: total }; }
