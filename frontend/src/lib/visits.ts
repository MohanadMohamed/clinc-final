import { z } from "zod"
import { csrf, getCsrfToken } from "./api"

const summary = z.object({id:z.string().uuid(),patient_id:z.string().uuid(),appointment_id:z.string().uuid().nullable(),status:z.enum(["draft","finalized"]),revision:z.number(),created_at:z.string(),updated_at:z.string(),finalized_at:z.string().nullable()})
const detail = summary.extend({neurological_note:z.string(),psychiatric_note:z.string(),follow_up_plan:z.string()})
const history = z.object({revisions:z.array(z.object({revision:z.number(),actor_id:z.string(),event:z.string(),neurological_note:z.string(),psychiatric_note:z.string(),follow_up_plan:z.string(),occurred_at:z.string()})),addenda:z.array(z.object({id:z.string(),actor_id:z.string(),body:z.string(),occurred_at:z.string()}))})
export type Visit = z.infer<typeof detail>
export type VisitSummary = z.infer<typeof summary>
const page = z.object({items:z.array(summary),total:z.number(),page:z.number(),page_size:z.number()})
async function call<T>(path:string,schema:z.ZodType<T>,method="GET",body?:object):Promise<T>{
  if(method!=="GET") await csrf()
  const response=await fetch(path,{method,credentials:"same-origin",headers:method==="GET"?{}:{"Content-Type":"application/json","X-CSRF-Token":getCsrfToken()},body:body?JSON.stringify(body):undefined})
  if(!response.ok) throw new Error(response.status===409?"تغيّر السجل. حدّث الصفحة قبل المتابعة.":response.status===403?"ليس لديك صلاحية لعرض السجل السريري.":response.status===404?"السجل غير موجود.":response.status===422?"تحقق من الحقول المدخلة.":response.status===400?"لا يمكن إتمام العملية في حالة الزيارة الحالية.":"تعذر الاتصال بالخادم. حاول مجدداً.")
  return schema.parse(await response.json())
}
export const listVisits=(patientId?:string,pageNumber=1)=>call(`/api/visits?${new URLSearchParams({...(patientId?{patient_id:patientId}:{}),page:String(pageNumber)})}`,page)
export const getVisit=(id:string)=>call(`/api/visits/${id}`,detail)
export const getVisitHistory=(id:string)=>call(`/api/visits/${id}/history`,history)
export const createVisit=(patient_id:string,appointment_id?:string)=>call("/api/visits",detail,"POST",{patient_id,...(appointment_id?{appointment_id}:{})})
export const saveVisit=(id:string,revision:number,notes:{neurological_note:string;psychiatric_note:string;follow_up_plan:string})=>call(`/api/visits/${id}`,detail,"PATCH",{expected_revision:revision,...notes})
export const finalizeVisit=(id:string,revision:number)=>call(`/api/visits/${id}/finalize`,detail,"POST",{expected_revision:revision})
