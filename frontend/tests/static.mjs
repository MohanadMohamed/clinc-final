import { chromium } from '@playwright/test'

const origin = 'https://localhost:8443'
const browser = await chromium.launch({headless:true,executablePath:'/usr/bin/google-chrome',args:['--no-sandbox']})
const failures = []
const assets = new Set()
async function signIn(username) {
  const context = await browser.newContext({ignoreHTTPSErrors:true})
  const page = await context.newPage()
  page.on('pageerror',error=>failures.push(error.message))
  page.on('console',message=>{
    if(message.type()==='error'&&!/Failed to load resource: the server responded with a status of 401/.test(message.text()))failures.push(message.text())
  })
  page.on('request',request=>{
    const url=request.url()
    if(url.startsWith('http')&&!url.startsWith(origin+'/'))failures.push(`external asset request: ${new URL(url).origin}`)
    if(url.includes('/app/assets/'))assets.add(url)
  })
  await page.goto(origin+'/app/login')
  await page.getByRole('heading',{name:'مرحباً بعودتك'}).waitFor()
  await page.getByLabel('اسم المستخدم').fill(username)
  await page.getByLabel('كلمة المرور').fill(process.env.TEST_PASSWORD)
  const login=page.waitForResponse(response=>response.url().endsWith('/api/auth/login'))
  await page.getByRole('button',{name:'تسجيل الدخول'}).click()
  if((await login).status()!==200)throw Error(`${username} login failed`)
  await page.getByText('مساحة العمل جاهزة').waitFor()
  if(new URL(page.url()).pathname!=='/app/')throw Error(`wrong post-login route: ${page.url()}`)
  return {context,page}
}
let doctor,reception
try {
  doctor=await signIn('synthetic.doctor')
  const html=await doctor.page.locator('html').evaluate(element=>({lang:element.lang,dir:element.dir}))
  if(html.lang!=='ar'||html.dir!=='rtl')throw Error('Arabic RTL missing')
  await doctor.page.getByRole('link',{name:'المرضى'}).click()
  if(new URL(doctor.page.url()).pathname!=='/app/patients')throw Error('React Router basename missing')
  await doctor.page.reload()
  await doctor.page.getByRole('heading',{name:'المرضى'}).waitFor()
  await doctor.page.goto(origin+'/app/workspace')
  await doctor.page.getByRole('heading',{name:'الزيارات السريرية'}).waitFor()
  reception=await signIn('synthetic.reception')
  if(await reception.page.getByRole('link',{name:'مساحة الطبيب'}).count())throw Error('doctor navigation leaked to reception')
  if((await reception.context.request.get(origin+'/api/visits')).status()!==403)throw Error('reception visit API not denied')
  if((await doctor.context.request.get(origin+'/api/me')).status()!==200)throw Error('doctor session lost')
  if((await doctor.context.request.get(origin+'/api/health')).status()!==200)throw Error('API health missing')
  if((await doctor.context.request.get(origin+'/api/unknown',{headers:{accept:'text/html'}})).status()!==404)throw Error('unknown API swallowed by SPA')
  if((await doctor.context.request.get(origin+'/docs')).status()!==200)throw Error('FastAPI docs unavailable')
  if((await doctor.context.request.get(origin+'/openapi.json')).status()!==200)throw Error('OpenAPI unavailable')
  if(![...assets].some(url=>url.endsWith('.js'))||![...assets].some(url=>url.endsWith('.css')))throw Error('local bundled scripts/styles not loaded')
  if(failures.length)throw Error(failures.join(' | '))
  console.log('PASS static browser: built React on FastAPI only, /app history fallback, local assets, Arabic RTL, two roles, API/docs isolation, no unexpected console errors')
} catch(error) {console.error(error);process.exitCode=1}
finally {await Promise.allSettled([doctor?.context?.close(),reception?.context?.close()]);await browser.close()}
