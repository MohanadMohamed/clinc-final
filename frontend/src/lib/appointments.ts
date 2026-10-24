import { z } from "zod"
import { csrf, getCsrfToken } from "./api"
export const appointmentSchema = z.object({ id:z.string().uuid(), patient_id:z.string().uuid(), kind:z.enum(["first_visit","follow_up"]), status:z.enum(["scheduled","cancelled"]), start_at:z.string(), end_at:z.string(), created_at:z.string(), updated_at:z.string() })
export type Appointment = z.infer<typeof appointmentSchema>
const pageSchema = z.object({items:z.array(appointmentSchema), total:z.number().int(), page:z.number().int(), page_size:z.number().int()})
export type AppointmentPage = z.infer<typeof pageSchema>
export class AppointmentError extends Error { constructor(public status:number, message:string){super(message)} }
async function request<T>(url:string, schema:z.ZodType<T>, init?:RequestInit):Promise<T> {
  const response=await fetch(url,{credentials:"same-origin",...init})
  if(!response.ok){
    const message=response.status===409?"الموعد محجوز بالفعل. تم تحديث القائمة، اختر وقتاً آخر.":response.status===400?"الوقت خارج ساعات العمل أو لا يطابق مدة الزيارة، أو لم يعد الموعد قابلاً للتعديل.":response.status===401?"انتهت الجلسة. سجّل الدخول مرة أخرى":response.status===403?"تعذر التحقق من الطلب. حدّث الصفحة وحاول مجدداً":response.status===404?"لم يعد الموعد أو المريض متاحاً":response.status===422?"تحقق من نوع الزيارة والأوقات المحددة":"تعذر الاتصال بالخادم. حاول مرة أخرى"
    throw new AppointmentError(response.status,message)
  }
  return schema.parse(await response.json())
}
export function getAppointments(start:string,end:string,status:"scheduled"|"cancelled"|"all",page:number){const qs=new URLSearchParams({start,end,page:String(page),page_size:"100"});if(status!=="all")qs.set("status",status);return request(`/api/appointments?${qs}`,pageSchema)}
async function mutate(url:string,body?:object){await csrf();return request(url,appointmentSchema,{method:"POST",headers:{"X-CSRF-Token":getCsrfToken(),...(body?{"Content-Type":"application/json"}:{})},...(body?{body:JSON.stringify(body)}:{})})}
export type TimeInput={start_at:string;end_at:string}
export function createAppointment(input:TimeInput & {patient_id:string;kind:"first_visit"|"follow_up"}){return mutate("/api/appointments",input)}
export function rescheduleAppointment(id:string,input:TimeInput){return mutate(`/api/appointments/${id}/reschedule`,input)}
export function cancelAppointment(id:string){return mutate(`/api/appointments/${id}/cancel`)}
