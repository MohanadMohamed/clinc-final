import { z } from "zod"

const userSchema = z.object({ id: z.string().uuid(), username: z.string(), role: z.enum(["doctor", "receptionist"]) })
export type User = z.infer<typeof userSchema>
let csrfToken: string | undefined

async function request<T>(path: string, schema: z.ZodType<T>, init: RequestInit = {}): Promise<T> {
  const response = await fetch(path, { ...init, credentials: "same-origin", headers: { ...(init.body ? { "Content-Type": "application/json" } : {}), ...(init.method && init.method !== "GET" ? { "X-CSRF-Token": csrfToken ?? "" } : {}), ...init.headers } })
  if (!response.ok) throw new Error(response.status === 401 ? "بيانات الدخول غير صحيحة أو انتهت الجلسة" : response.status === 403 ? "تعذر التحقق من الطلب. حدّث الصفحة وحاول مجدداً" : "تعذر الاتصال بالخادم. حاول مرة أخرى")
  return schema.parse(response.status === 204 ? null : await response.json())
}
export async function csrf() { const value = await request("/api/auth/csrf", z.object({ csrf_token: z.string() })); csrfToken = value.csrf_token }
export const me = () => request("/api/me", userSchema)
export async function login(username: string, password: string) { await csrf(); const user = await request("/api/auth/login", userSchema, { method: "POST", body: JSON.stringify({ username, password }) }); await csrf(); return user }
export async function logout() { await csrf(); await request("/api/auth/logout", z.null(), { method: "POST" }); csrfToken = undefined }

export function getCsrfToken() { return csrfToken ?? "" }
