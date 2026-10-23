import { useQuery } from "@tanstack/react-query"
import { Route, Routes, Link } from "react-router-dom"
import { z } from "zod"

async function checkHealth(signal: AbortSignal) {
  await Promise.all([
    ["/api/health", "ok"], ["/api/health/ready", "ready"],
  ].map(async ([url, expected]) => {
    const response = await fetch(url, { signal: AbortSignal.any([signal, AbortSignal.timeout(5000)]) })
    if (!response.ok) throw new Error("Unavailable")
    z.object({ status: z.literal(expected) }).parse(await response.json())
  }))
  return true
}

function Home() {
  const health = useQuery({ queryKey: ["health"], queryFn: ({ signal }) => checkHealth(signal), retry: false })
  return <main className="mx-auto flex max-w-3xl flex-col gap-6 p-8">
    <h1 className="text-2xl font-semibold">عيادة المخ والأعصاب والطب النفسي</h1>
    <p>بيئة التطوير الأولية</p>
    <p role="status" aria-live="polite">{health.isPending ? "جارٍ التحقق من الاتصال…" : health.isError ? "تعذر الاتصال بالخادم أو قاعدة البيانات" : "الخادم وقاعدة البيانات متصلان"}</p>
  </main>
}

export default function App() {
  return <Routes><Route path="/" element={<Home />} />
    <Route path="*" element={<main className="p-8"><h1>الصفحة غير موجودة</h1><Link to="/">العودة للرئيسية</Link></main>} />
  </Routes>
}
