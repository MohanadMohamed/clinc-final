import { z } from "zod"
import { csrf } from "./api"

export const patientSchema = z.object({ id: z.string().uuid(), full_name: z.string(), phone: z.string(), birth_date: z.string().nullable(), active: z.boolean(), created_at: z.string(), updated_at: z.string(), archived_at: z.string().nullable() })
export type Patient = z.infer<typeof patientSchema>
export const patientPage = z.object({ items: z.array(patientSchema), total: z.number(), page: z.number(), page_size: z.number() })
export type PatientInput = { full_name: string; phone: string; birth_date: string | null; confirm_duplicate?: boolean }
async function read<T>(path: string, schema: z.ZodType<T>, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(path, { credentials: "same-origin", ...init })
  } catch {
    throw new Error("تعذر الاتصال بالخادم. حاول مرة أخرى")
  }
  if (!response.ok) {
    if (response.status === 401) throw new Error("انتهت الجلسة. سجّل الدخول مرة أخرى")
    if (response.status === 400) throw new Error("قد يكون المريض مسجلاً بالفعل، أو لم يعد بالإمكان تعديل السجل")
    if (response.status === 404) throw new Error("لم يعد سجل المريض متاحاً")
    if (response.status === 422) throw new Error("تحقق من الاسم ورقم الهاتف وتاريخ الميلاد")
    throw new Error("تعذر إكمال الطلب. حاول مرة أخرى")
  }
  return schema.parse(await response.json())
}
async function write<T>(path: string, method: string, schema: z.ZodType<T>, body?: object) {
  await csrf()
  // The synchronizer token is held only in memory; fetch a fresh one for each mutation.
  const token = getCsrfToken()
  return read(path, schema, { method, headers: { "Content-Type": "application/json", "X-CSRF-Token": token }, ...(body ? { body: JSON.stringify(body) } : {}) })
}
// Supplied by the same in-memory auth client, never persisted in browser storage.
import { getCsrfToken } from "./api"
export function listPatients(search: string, page: number) { const q = new URLSearchParams({ page: String(page), page_size: "10" }); if (search) q.set("search", search); return read(`/api/patients?${q}`, patientPage) }
export const getPatient = (id: string) => read(`/api/patients/${id}`, patientSchema)
export const createPatient = (data: PatientInput) => write("/api/patients", "POST", patientSchema, data)
export const updatePatient = (id: string, data: Partial<PatientInput>) => write(`/api/patients/${id}`, "PATCH", patientSchema, data)
export const archivePatient = (id: string) => write(`/api/patients/${id}/archive`, "POST", patientSchema)
