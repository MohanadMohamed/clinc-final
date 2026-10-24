import {chromium} from '@playwright/test'
const browser=await chromium.launch({headless:true,executablePath:'/usr/bin/google-chrome',args:['--no-sandbox']})
const errors=[]
async function login(name){const context=await browser.newContext({ignoreHTTPSErrors:true});const page=await context.newPage();page.on('pageerror',error=>errors.push(error.message));page.on('console',message=>{if(message.type()==='error'&&!/Failed to load resource: the server responded with a status of (401|403|404)/.test(message.text()))errors.push(message.text())});await page.goto('https://localhost:5173/login');await page.getByLabel('اسم المستخدم').fill(name);await page.getByLabel('كلمة المرور').fill(process.env.TEST_PASSWORD);await page.getByRole('button',{name:'تسجيل الدخول'}).click();await page.getByText('مساحة العمل جاهزة').waitFor();return {context,page}}
let doctor,reception
try{
 doctor=await login('synthetic.doctor');await doctor.page.getByRole('link',{name:'مساحة الطبيب'}).click();await doctor.page.getByRole('heading',{name:'الزيارات السريرية'}).waitFor()
 let day=new Date(Date.now()+10*86400000).toISOString().slice(0,10);while(new Date(day+'T12:00:00Z').getUTCDay()===5)day=new Date(new Date(day+'T12:00:00Z').getTime()+86400000).toISOString().slice(0,10)
 await doctor.page.getByLabel('يوم الموعد').fill(day)
 const created=doctor.page.waitForResponse(r=>r.url().endsWith('/api/visits')&&r.request().method()==='POST');await doctor.page.getByRole('button',{name:'بدء الزيارة',exact:true}).first().click();const creation=await created;if(creation.status()!==201)throw Error('visit create '+creation.status());const id=(await creation.json()).id
 await doctor.page.getByRole('heading',{name:/زيارة سجل ثابت اصطناعي/}).waitFor()
 await doctor.page.getByLabel('الملاحظات العصبية').fill('ملاحظة اصطناعية للعصب')
 doctor.page.once('dialog',dialog=>dialog.dismiss());await doctor.page.getByRole('link',{name:'المرضى'}).click();await doctor.page.getByText('تغييرات غير محفوظة').waitFor()
 await doctor.page.getByLabel('الملاحظات النفسية').fill('ملاحظة اصطناعية للنفس')
 await doctor.page.getByLabel('خطة المتابعة').fill('خطة متابعة اصطناعية')
 await doctor.page.getByRole('button',{name:'حفظ المسودة'}).click();await doctor.page.getByText('تم حفظ المسودة بنجاح').waitFor()
 await doctor.page.getByRole('button',{name:'العودة إلى القائمة'}).click();await doctor.page.getByRole('button',{name:'عرض الزيارة'}).first().click();await doctor.page.getByLabel('خطة المتابعة').waitFor();if(await doctor.page.getByLabel('خطة المتابعة').inputValue()!=='خطة متابعة اصطناعية')throw Error('draft did not persist')
 await doctor.page.getByRole('heading',{name:'سجل الزيارة'}).waitFor();doctor.page.once('dialog',dialog=>dialog.accept());await doctor.page.getByRole('button',{name:'اعتماد الزيارة'}).click();await doctor.page.getByText('تم اعتماد الزيارة').waitFor()
 reception=await login('synthetic.reception');if(await reception.page.getByRole('link',{name:'مساحة الطبيب'}).count())throw Error('reception menu leak');await reception.page.goto('https://localhost:5173/workspace');await reception.page.getByText('مساحة العمل جاهزة').waitFor();const denied=await reception.context.request.get(`https://localhost:5173/api/visits/${id}`);if(denied.status()!==403)throw Error('reception direct API '+denied.status());const list=await reception.context.request.get('https://localhost:5173/api/visits');if(list.status()!==403)throw Error('reception list API '+list.status());if(errors.length)throw Error(errors.join(' | '));console.log('PASS browser: doctor scheduled visit, save, history, unsaved warning, finalize; receptionist route hidden and API 403')
}catch(error){console.error(error);process.exitCode=1}finally{await Promise.allSettled([doctor?.context?.close(),reception?.context?.close()]);await browser.close()}
