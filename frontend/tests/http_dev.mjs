import { chromium } from '@playwright/test'

const base = 'http://127.0.0.1:5173'
const browser = await chromium.launch({ headless: true, executablePath: '/usr/bin/google-chrome', args: ['--no-sandbox'] })
const context = await browser.newContext()
const page = await context.newPage()
const errors = []
page.on('pageerror', error => errors.push(error.message))
page.on('console', message => {
  if (message.type() === 'error' && !/Failed to load resource: the server responded with a status of (401|403)/.test(message.text())) errors.push(message.text())
})
async function signIn(username, password) {
  await page.goto(base + '/login')
  await page.getByLabel('اسم المستخدم').fill(username)
  await page.getByLabel('كلمة المرور').fill(password)
  await page.getByRole('button', { name: 'تسجيل الدخول' }).click()
}
try {
  await page.goto(base + '/login')
  if (await page.locator('html').getAttribute('dir') !== 'rtl') throw Error('RTL missing')
  const csrf = await page.evaluate(async () => (await fetch('/api/auth/csrf')).status)
  if (csrf !== 200) throw Error('CSRF handshake failed: ' + csrf)
  const missingCsrf = await page.evaluate(async () => (await fetch('/api/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username: 'synthetic.doctor', password: 'invalid' }) })).status)
  if (missingCsrf !== 403) throw Error('Missing CSRF was not denied')
  await signIn('synthetic.doctor', 'invalid-password')
  await page.getByRole('alert').waitFor()
  await signIn('synthetic.reception', process.env.TEST_PASSWORD)
  await page.getByText('مساحة العمل جاهزة').waitFor()
  const receptionRole = await page.evaluate(async () => (await (await fetch('/api/me')).json()).role)
  if (receptionRole !== 'receptionist') throw Error('Reception login failed')
  const forbidden = await page.evaluate(async () => (await fetch('/api/visits')).status)
  if (forbidden !== 403) throw Error('Reception clinical access was not denied')
  for (const route of ['/api/patients', '/api/appointments']) {
    const status = await page.evaluate(async route => (await fetch(route)).status, route)
    if (status !== 200) throw Error(route + ' returned ' + status)
  }
  await page.reload()
  await page.getByText('مساحة العمل جاهزة').waitFor()
  await page.getByRole('button', { name: 'تسجيل الخروج' }).click()
  await page.getByRole('heading', { name: 'مرحباً بعودتك' }).waitFor()
  const anonymous = await page.evaluate(async () => (await fetch('/api/me')).status)
  if (anonymous !== 401) throw Error('Logout session remains usable')
  await signIn('synthetic.doctor', process.env.TEST_PASSWORD)
  await page.getByText('مساحة الطبيب').waitFor()
  await page.reload()
  await page.getByText('مساحة الطبيب').waitFor()
  if (errors.length) throw Error('Browser console errors: ' + errors.join(' | '))
  console.log('PASS HTTP loopback Playwright: CSRF, invalid login, both roles, patient/appointment reads, clinical 403, logout, refresh, RTL, console')
} finally {
  await browser.close()
}
