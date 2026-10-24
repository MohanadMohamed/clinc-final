const clock = new Intl.DateTimeFormat("en-GB", { timeZone: "Africa/Cairo", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hourCycle: "h23" })
export function cairoDate(date = new Date()): string {
  const parts = Object.fromEntries(clock.formatToParts(date).map(p => [p.type, p.value]))
  return `${parts.year}-${parts.month}-${parts.day}`
}
export function cairoClock(date: Date): string {
  return new Intl.DateTimeFormat("ar-EG", {timeZone:"Africa/Cairo", hour:"2-digit", minute:"2-digit", hourCycle:"h23"}).format(date)
}
export function cairoDayLabel(day: string): string {
  const date = new Date(`${day}T12:00:00Z`)
  return new Intl.DateTimeFormat("ar-EG", {timeZone:"Africa/Cairo", dateStyle:"full"}).format(date)
}
export function localCandidates(day: string, time: string): string[] {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(day) || !/^\d{2}:\d{2}$/.test(time)) return []
  const [year, month, date] = day.split("-").map(Number)
  const [hour, minute] = time.split(":").map(Number)
  if (month < 1 || month > 12 || hour > 23 || minute > 59 || !Number.isFinite(Date.UTC(year, month - 1, date, hour, minute)) || new Date(Date.UTC(year, month - 1, date)).getUTCDate() !== date) return []
  const wall = Date.UTC(year, month - 1, date, hour, minute)
  return [120, 180].map(offset => new Date(wall - offset * 60_000)).filter(candidate => {
    const parts = Object.fromEntries(clock.formatToParts(candidate).map(p => [p.type, p.value]))
    return `${parts.year}-${parts.month}-${parts.day}` === day && `${parts.hour}:${parts.minute}` === time
  }).map(candidate => candidate.toISOString())
}
export function cairoDayBounds(day: string): {start:string;end:string} {
  const next = new Date(`${day}T12:00:00Z`)
  if (Number.isNaN(next.getTime())) throw new Error("تاريخ غير صالح")
  next.setUTCDate(next.getUTCDate() + 1)
  const nextDay = next.toISOString().slice(0, 10)
  const first = (value:string) => {
    for (let minute=0; minute<180; minute++) {
      const time = `${String(Math.floor(minute/60)).padStart(2,"0")}:${String(minute%60).padStart(2,"0")}`
      const matches = localCandidates(value,time)
      if (matches.length) return matches[0]
    }
    throw new Error("تعذر تحديد بداية اليوم في القاهرة")
  }
  return {start:first(day),end:first(nextDay)}
}
