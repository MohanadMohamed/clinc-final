import { chromium } from '@playwright/test'

const origin = 'https://localhost:8443'
const browser = await chromium.launch({ headless: true, executablePath: '/usr/bin/google-chrome', args: ['--no-sandbox'] })
const failures = []
const assets = new Set()
const apiEvents = []
async function contextPage() {
  const context = await browser.newContext({ ignoreHTTPSErrors: true })
  const page = await context.newPage()
  page.on('pageerror', error => failures.push(error.message))
  page.on('console', message => {
    if (message.type() === 'error' && !/Failed to load resource: the server responded with a status of (401|403|404)/.test(message.text())) failures.push(message.text())
  })
  page.on('request', request => {
    const url = request.url()
    if (url.startsWith('http') && !url.startsWith(origin + '/')) failures.push('External request: ' + url)
    if (url.includes('/app/assets/')) assets.add(url)
  })
  page.on('response', response => {
    if (response.url().includes('/api/')) apiEvents.push(response.status() + ' ' + new URL(response.url()).pathname)
  })
  return { context, page }
}
async function signIn(page, username, password) {
  await page.goto(origin + '/app/login')
  await page.getByLabel('اسم المستخدم').fill(username)
  await page.getByLabel('كلمة المرور').fill(password)
  const response = page.waitForResponse(item => item.url().endsWith('/api/auth/login'), { timeout: 8000 })
  await page.getByRole('button', { name: 'تسجيل الدخول' }).click()
  try { return (await response).status() }
  catch { throw Error('Login request missing; API: ' + apiEvents.join(', ') + '; alerts: ' + (await page.getByRole('alert').allTextContents()).join(' | ') + '; console: ' + failures.join(' | ')) }
}
let doctor, reception
try {
  doctor = await contextPage()
  await doctor.page.goto(origin + '/app/login')
  await doctor.page.getByText('نسخة عرض عامة — بيانات اصطناعية فقط').waitFor()
  if (await doctor.page.locator('html').getAttribute('dir') !== 'rtl') throw Error('Arabic RTL missing')
  const anonymous = await doctor.context.request.get(origin + '/api/patients')
  if (anonymous.status() !== 401) throw Error('Anonymous patient access was not denied')
  if (await signIn(doctor.page, 'synthetic.doctor', 'invalid-password') !== 401) throw Error('Invalid login was not rejected')
  await doctor.page.getByRole('alert').waitFor()
  const doctorLogin = await signIn(doctor.page, 'synthetic.doctor', process.env.TEST_PASSWORD)
  if (doctorLogin !== 200) throw Error('Doctor login returned ' + doctorLogin + ': ' + failures.join(' | '))
  try { await doctor.page.getByText('مساحة العمل جاهزة').waitFor({timeout:10000}) }
  catch { throw Error('Post-login page ' + doctor.page.url() + '; alerts: ' + (await doctor.page.getByRole('alert').allTextContents()).join(' | ') + '; console: ' + failures.join(' | ')) }
  const cookies = await doctor.context.cookies(origin)
  const session = cookies.find(cookie => cookie.name === '__Host-clinic_session')
  if (!session?.secure || !session.httpOnly || session.sameSite !== 'Strict') throw Error('Production session cookie attributes missing')
  await doctor.page.goto(origin + '/app/patients')
  await doctor.page.getByRole('heading', { name: 'المرضى' }).waitFor()
  await doctor.page.reload()
  await doctor.page.getByRole('heading', { name: 'المرضى' }).waitFor()
  if ((await doctor.context.request.get(origin + '/api/appointments')).status() !== 200) throw Error('Doctor appointments unavailable')
  if ((await doctor.context.request.get(origin + '/api/billing/fees')).status() !== 200) throw Error('Doctor billing unavailable')
  await doctor.page.goto(origin + '/app/workspace')
  await doctor.page.getByRole('heading', { name: 'الزيارات السريرية' }).waitFor()
  reception = await contextPage()
  if (await signIn(reception.page, 'synthetic.reception', process.env.TEST_PASSWORD) !== 200) throw Error('Reception login failed')
  await reception.page.getByText('مساحة العمل جاهزة').waitFor()
  if (await reception.page.getByRole('link', { name: 'مساحة الطبيب' }).count()) throw Error('Doctor menu exposed to reception')
  if ((await reception.context.request.get(origin + '/api/visits')).status() !== 403) throw Error('Reception clinical API was not denied')
  if ((await reception.context.request.get(origin + '/docs')).status() !== 404) throw Error('Public API docs exposed')
  if ((await reception.context.request.get(origin + '/openapi.json')).status() !== 404) throw Error('Public OpenAPI exposed')
  const headers = (await reception.context.request.get(origin + '/app/')).headers()
  if (!headers['content-security-policy']?.includes("frame-ancestors 'none'")) throw Error('CSP missing')
  if (!headers['x-frame-options'] || !headers['referrer-policy']) throw Error('Security headers missing')
  await reception.page.getByRole('button', { name: 'تسجيل الخروج' }).click()
  await reception.page.getByRole('heading', { name: 'مرحباً بعودتك' }).waitFor()
  if ((await reception.context.request.get(origin + '/api/me')).status() !== 401) throw Error('Logout did not revoke session')
  if (![...assets].some(url => url.endsWith('.js')) || ![...assets].some(url => url.endsWith('.css'))) throw Error('Bundled assets not loaded')
  if (failures.length) throw Error(failures.join(' | '))
  console.log('PASS Render prototype browser: built assets, deep links, Arabic RTL, demo label, login/logout, Secure cookie, both roles, patient/appointment/billing reads, clinical 403, headers, no external requests or console errors')
} finally {
  await Promise.allSettled([doctor?.context?.close(), reception?.context?.close()])
  await browser.close()
}
