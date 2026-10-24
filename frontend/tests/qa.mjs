import { chromium } from '@playwright/test'

const base = 'https://localhost:5173'
const browser = await chromium.launch({headless:true,executablePath:'/usr/bin/google-chrome',args:['--no-sandbox']})
const errors = []
async function login(username, viewport) {
  const context = await browser.newContext({ignoreHTTPSErrors:true,viewport})
  const page = await context.newPage()
  page.on('pageerror', error => errors.push(error.message))
  page.on('console', message => {
    if (message.type()==='error' && !/Failed to load resource: (net::ERR_FAILED|the server responded with a status of 401)/.test(message.text())) errors.push(`${message.text()} @ ${message.location().url}`)
  })
  await page.goto(base+'/login')
  await page.getByLabel('اسم المستخدم').fill(username)
  await page.getByLabel('كلمة المرور').fill(process.env.TEST_PASSWORD)
  const attempt=page.waitForResponse(response=>response.url().endsWith('/api/auth/login'))
  await page.getByRole('button',{name:'تسجيل الدخول'}).click()
  const loginResponse=await attempt
  if(loginResponse.status()!==200)throw Error(`synthetic ${username} login returned HTTP ${loginResponse.status()}`)
  await page.getByText('مساحة العمل جاهزة').waitFor()
  return {context,page}
}
async function layout(page,width,height) {
  await page.setViewportSize({width,height})
  const geometry=await page.evaluate(()=>({width:innerWidth,document:document.documentElement.scrollWidth,lang:document.documentElement.lang,dir:document.documentElement.dir}))
  if(geometry.width!==width||geometry.document>width||geometry.lang!=='ar'||geometry.dir!=='rtl')throw Error(`RTL/layout ${width}: ${JSON.stringify(geometry)}`)
  if(width===390){await page.getByRole('button',{name:'فتح القائمة'}).click();await page.getByRole('link',{name:'المرضى'}).waitFor();await page.getByRole('button',{name:'إغلاق القائمة'}).first().click()}
}
let doctor,reception
try {
  doctor=await login('synthetic.doctor',{width:1440,height:900})
  reception=await login('synthetic.reception',{width:390,height:844})
  const dm=await doctor.context.request.get(base+'/api/me')
  const rm=await reception.context.request.get(base+'/api/me')
  if((await dm.json()).role!=='doctor'||(await rm.json()).role!=='receptionist')throw Error('independent browser sessions changed roles')
  await layout(doctor.page,1440,900)
  await layout(reception.page,390,844)
  await doctor.page.getByRole('link',{name:'المواعيد'}).click();await doctor.page.getByRole('heading',{name:'المواعيد'}).waitFor();await layout(doctor.page,1440,900)
  await doctor.page.getByRole('link',{name:'الفواتير'}).click();await doctor.page.getByRole('heading',{name:'الفواتير والتحصيل'}).waitFor();await layout(doctor.page,1440,900)
  await reception.page.getByRole('button',{name:'فتح القائمة'}).click();await reception.page.getByRole('link',{name:'المواعيد'}).click();await reception.page.getByRole('heading',{name:'المواعيد'}).waitFor();await layout(reception.page,390,844)
  await reception.page.getByRole('button',{name:'فتح القائمة'}).click();await reception.page.getByRole('link',{name:'الفواتير'}).click();await reception.page.getByRole('heading',{name:'الفواتير والتحصيل'}).waitFor();await layout(reception.page,390,844)
  await reception.page.route('**/api/patients?*',route=>route.abort('failed'))
  await reception.page.getByRole('button',{name:'فتح القائمة'}).click();await reception.page.getByRole('link',{name:'المرضى'}).click()
  await reception.page.getByRole('alert').getByText('تعذر الاتصال بالخادم').waitFor()
  await reception.page.unroute('**/api/patients?*')
  await reception.page.getByRole('button',{name:'إعادة المحاولة'}).click()
  await reception.page.getByText('عدد السجلات:').waitFor()
  await layout(reception.page,390,844)
  await doctor.page.getByRole('button',{name:'تسجيل الخروج'}).click()
  await doctor.page.getByRole('heading',{name:'مرحباً بعودتك'}).waitFor()
  if((await doctor.context.request.get(base+'/api/me')).status()!==401)throw Error('doctor logout did not invalidate session')
  if((await reception.context.request.get(base+'/api/me')).status()!==200)throw Error('doctor logout invalidated reception session')
  if(errors.length)throw Error('unexpected browser errors: '+errors.join(' | '))
  console.log('PASS QA browser: isolated doctor/reception sessions, RTL 1440x900 and 390x844, responsive pages, network-error retry, logout isolation, no unexpected console errors')
} catch(error) {console.error(error);process.exitCode=1}
finally {await Promise.allSettled([doctor?.context?.close(),reception?.context?.close()]);await browser.close()}
