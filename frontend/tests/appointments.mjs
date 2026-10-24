import {chromium} from '@playwright/test'
const browser=await chromium.launch({headless:true,executablePath:'/usr/bin/google-chrome',args:['--no-sandbox']})
const failures=[]
const conflicts=[]
const make=async(name)=>{const ctx=await browser.newContext({ignoreHTTPSErrors:true});const page=await ctx.newPage();page.on('pageerror',e=>failures.push(e.message));page.on('response',r=>{if(r.url().includes('/api/appointments')&&r.request().method()==='POST'&&r.status()===409)conflicts.push(r.url())});page.on('console',m=>{if(m.type()==='error'&&!/Failed to load resource: the server responded with a status of (401|404|409)/.test(m.text()))failures.push(m.text())});await page.goto('https://localhost:5173/login');await page.getByLabel('اسم المستخدم').fill(name);await page.getByLabel('كلمة المرور').fill(process.env.TEST_PASSWORD);await page.getByRole('button',{name:'تسجيل الدخول'}).click();await page.getByText('مساحة العمل جاهزة').waitFor();await page.getByRole('link',{name:'المواعيد'}).click();return {ctx,page}}
let a,b
try{
 const anonymous=await browser.newContext({ignoreHTTPSErrors:true});const denied=await anonymous.request.get('https://localhost:5173/api/appointments');if(denied.status()!==401)throw Error('anonymous appointment request must be denied');await anonymous.close()
 a=await make('synthetic.reception');b=await make('synthetic.doctor')
 let day=new Date(Date.now()+10*86400000).toISOString().slice(0,10)
 while(new Date(day+'T12:00:00Z').getUTCDay()===5)day=new Date(new Date(day+'T12:00:00Z').getTime()+86400000).toISOString().slice(0,10)
 async function prepare(page,start='10:00',end='10:30'){await page.getByLabel('اليوم',{exact:true}).fill(day);await page.getByRole('button',{name:'حجز موعد',exact:true}).click();const d=page.getByRole('dialog',{name:'حجز موعد'});await d.getByLabel('ابحث عن مريض بالاسم أو الهاتف').fill('سجل ثابت اصطناعي');await d.locator('#appointment-patient option').nth(1).waitFor({state:'attached'});await d.locator('#appointment-patient').selectOption(await d.locator('#appointment-patient option').nth(1).getAttribute('value'));await d.getByLabel('من').fill(start);await d.getByLabel('إلى').fill(end);return d}
 const receptionBooking=await prepare(a.page,'09:00','09:30');await receptionBooking.getByRole('button',{name:'حجز الموعد'}).click();await a.page.getByText('عدد المواعيد المطابقة: 1').waitFor();await b.page.getByLabel('اليوم',{exact:true}).fill(day);await b.page.getByText('عدد المواعيد المطابقة: 1').waitFor();await b.page.getByText('سجل ثابت اصطناعي').waitFor();
 const [da,db]=await Promise.all([prepare(a.page),prepare(b.page)])
 await Promise.all([da.getByRole('button',{name:'حجز الموعد'}).click(),db.getByRole('button',{name:'حجز الموعد'}).click()])
 await Promise.race([da.getByRole('alert').waitFor(),db.getByRole('alert').waitFor()])
 const loser=await da.getByRole('alert').count()?a:b,winner=loser===a?b:a
 const alert=loser.page.getByRole('dialog',{name:'حجز موعد'}).getByRole('alert');if(!/محجوز بالفعل/.test(await alert.textContent())||conflicts.length!==1)throw Error('expected one HTTP 409 and explicit Arabic booking feedback')
 await loser.page.getByRole('dialog',{name:'حجز موعد'}).getByRole('button',{name:'إلغاء'}).click()
 await winner.page.getByText('عدد المواعيد المطابقة: 2').waitFor()
 await loser.page.reload();await loser.page.getByLabel('اليوم',{exact:true}).fill(day);await loser.page.getByText('عدد المواعيد المطابقة: 2').waitFor()
 await winner.page.getByRole('button',{name:'إعادة جدولة'}).nth(1).click();let d=winner.page.getByRole('dialog',{name:'إعادة جدولة الموعد'});await d.getByLabel('من').fill('11:00');await d.getByLabel('إلى').fill('11:30');const changed=winner.page.waitForResponse(r=>r.url().endsWith('/reschedule')&&r.request().method()==='POST');await d.getByRole('button',{name:'تأكيد الموعد الجديد'}).click();const changedResponse=await changed;if(changedResponse.status()!==200)throw Error('reschedule HTTP '+changedResponse.status());await d.waitFor({state:'detached'});const changedBody=await changedResponse.json();const expectedTime=new Intl.DateTimeFormat('ar-EG',{timeZone:'Africa/Cairo',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).format(new Date(changedBody.start_at));await winner.page.locator('time').filter({hasText:expectedTime}).first().waitFor()
 await winner.page.getByRole('button',{name:'إلغاء',exact:true}).nth(1).click();await winner.page.getByRole('dialog',{name:'تأكيد إلغاء الموعد'}).getByRole('button',{name:'تأكيد الإلغاء'}).click();await winner.page.getByText('عدد المواعيد المطابقة: 1').waitFor();await winner.page.getByLabel('الحالة').selectOption('all');await winner.page.getByText('عدد المواعيد المطابقة: 2').waitFor();await winner.page.locator('.appointment-status.cancelled').waitFor()
 if(failures.length)throw Error('console errors: '+failures.join(' | '))
 console.log('PASS browser: two sessions, one booking succeeds, 409 conflict displayed, refreshed count, reschedule, confirmed cancel, Cairo day view, no unexpected console/page errors')
}catch(e){console.error(e);process.exitCode=1}finally{await Promise.allSettled([a?.ctx?.close(),b?.ctx?.close()]);await browser.close()}
