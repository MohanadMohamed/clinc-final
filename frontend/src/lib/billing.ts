import { z } from "zod"
import { csrf, getCsrfToken } from "./api"

const fee = z.object({kind:z.enum(["first_visit","follow_up"]),amount_minor:z.number().int(),occurred_at:z.string()})
const invoice = z.object({id:z.string().uuid(),patient_id:z.string().uuid(),appointment_id:z.string().uuid().nullable(),visit_id:z.string().uuid().nullable(),kind:z.enum(["first_visit","follow_up"]),status:z.enum(["draft","issued","void"]),currency:z.literal("EGP"),base_minor:z.number().int(),adjustment_minor:z.number().int(),total_minor:z.number().int(),paid_minor:z.number().int(),balance_minor:z.number().int(),created_at:z.string()})
const payment = z.object({id:z.string().uuid(),invoice_id:z.string().uuid(),amount_minor:z.number().int(),currency:z.literal("EGP"),occurred_at:z.string(),reversed:z.boolean()})
const summary = z.object({day:z.string(),currency:z.literal("EGP"),received_minor:z.number().int(),reversed_minor:z.number().int(),net_minor:z.number().int()})
export type Invoice = z.infer<typeof invoice>
export type Payment = z.infer<typeof payment>
export type Fee = z.infer<typeof fee>
export function minorToText(value:number){const sign=value<0?"−":"";const absolute=Math.abs(value);return `${sign}${Math.floor(absolute/100).toLocaleString("ar-EG")}٫${String(absolute%100).padStart(2,"0")} ج.م`}
export function textToMinor(value:string){const cleaned=value.trim();if(!/^\d+(?:\.\d{1,2})?$/.test(cleaned))throw new Error("أدخل مبلغاً صحيحاً بالجنيه حتى منزلتين عشريتين");const [whole,cents=""]=cleaned.split(".");const result=Number(whole)*100+Number(cents.padEnd(2,"0"));if(!Number.isSafeInteger(result)||result<=0||result>2_000_000_000)throw new Error("المبلغ خارج النطاق المسموح");return result}
async function request<T>(url:string,schema:z.ZodType<T>,method="GET",body?:object):Promise<T>{if(method!=="GET")await csrf();const response=await fetch(url,{method,credentials:"same-origin",headers:method==="GET"?{}:{"Content-Type":"application/json","X-CSRF-Token":getCsrfToken()},body:body?JSON.stringify(body):undefined});if(!response.ok)throw new Error(response.status===409?"تعارض مع سجل محفوظ. حدّث البيانات وحاول مرة أخرى.":response.status===403?"ليس لديك صلاحية لهذا الإجراء.":response.status===404?"السجل غير موجود.":response.status===422?"تحقق من الحقول المدخلة.":response.status===400?"تعذر إتمام العملية: تحقق من الرصيد وحالة الفاتورة والموعد.":"تعذر الاتصال بالخادم. حاول مرة أخرى.");return schema.parse(await response.json())}
export const getFees=()=>request("/api/billing/fees",z.array(fee))
export const setFee=(kind:Fee["kind"],amount_minor:number,reason:string)=>request("/api/billing/fees",fee,"POST",{kind,amount_minor,reason})
export const listInvoices=(page=1)=>request(`/api/billing/invoices?page=${page}`,z.object({items:z.array(invoice),total:z.number(),page:z.number(),page_size:z.number()}))
export const getInvoice=(id:string)=>request(`/api/billing/invoices/${id}`,invoice)
export const getPayments=(id:string)=>request(`/api/billing/invoices/${id}/payments`,z.array(payment))
export const createInvoice=(data:{idempotency_key:string;patient_id:string;kind:Fee["kind"]})=>request("/api/billing/invoices",invoice,"POST",data)
export const issueInvoice=(id:string)=>request(`/api/billing/invoices/${id}/issue`,invoice,"POST")
export const recordPayment=(id:string,amount_minor:number,idempotency_key:string)=>request(`/api/billing/invoices/${id}/payments`,payment.omit({reversed:true}),"POST",{amount_minor,idempotency_key})
export const getDaily=(day:string)=>request(`/api/billing/summary/${day}`,summary)
