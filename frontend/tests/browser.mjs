import { chromium } from '@playwright/test'
import { spawn } from 'node:child_process'
const base = 'https://localhost:5173'
const browser = await chromium.launch({headless:true,executablePath:'/usr/bin/google-chrome',args:['--no-sandbox']})
const context = await browser.newContext({ignoreHTTPSErrors:true})
const page = await context.newPage()
const errors=[]
page.on('pageerror',e=>errors.push(e.message))
page.on('console',m=>{if(m.type()==='error'&&!/Failed to load resource: the server responded with a status of (401|404)/.test(m.text()))errors.push(m.text())})
async function signIn(name){await page.goto(base+'/login');await page.getByLabel('اسم المستخدم').fill(name);await page.getByLabel('كلمة المرور').fill(process.env.TEST_PASSWORD);await page.getByRole('button',{name:'تسجيل الدخول'}).click();await page.getByText('مساحة العمل جاهزة').waitFor()}
try{
 const anon=await context.request.get(base+'/api/patients');if(anon.status()!==401)throw Error('anonymous list was not denied')
 await page.goto(base+'/login');if(await page.locator('html').getAttribute('dir')!=='rtl')throw Error('RTL missing')
 await page.getByLabel('اسم المستخدم').fill('synthetic.reception');await page.getByLabel('كلمة المرور').fill('invalid-password');await page.getByRole('button',{name:'تسجيل الدخول'}).click();await page.getByRole('alert').waitFor()
 await signIn('synthetic.reception');if(await page.getByText('مساحة الطبيب').count())throw Error('reception role nav leaked')
 await page.getByRole('link',{name:'المرضى'}).click();await page.getByRole('button',{name:'إضافة مريض'}).click();const dialog=page.getByRole('dialog',{name:'إضافة مريض'});await dialog.getByLabel('الاسم الكامل').fill('مريض اصطناعي');await dialog.getByLabel('رقم الهاتف').fill('+201012345678');await dialog.getByRole('button',{name:'حفظ'}).click();await page.getByText('مريض اصطناعي').waitFor()
 await page.getByLabel('ابحث بالاسم أو رقم الهاتف').fill('مريض اصطناعي');await page.getByRole('button',{name:'بحث'}).click();await page.getByRole('button',{name:'عرض التفاصيل'}).click();await page.getByRole('dialog',{name:'تفاصيل المريض'}).getByText('مريض اصطناعي').waitFor()
 await page.getByRole('button',{name:'تعديل'}).click();const edit=page.getByRole('dialog',{name:'تعديل المريض'});await edit.getByLabel('الاسم الكامل').fill('مريض اصطناعي محدث');await edit.getByRole('button',{name:'حفظ'}).click();await page.getByRole('dialog',{name:'تفاصيل المريض'}).getByText('مريض اصطناعي محدث').waitFor()
 await page.getByRole('button',{name:'أرشفة'}).click();await page.getByRole('button',{name:'تأكيد الأرشفة'}).click();await page.getByText('مؤرشف').waitFor();await page.getByRole('button',{name:'إغلاق'}).click()
 await page.getByRole('button',{name:'إضافة مريض'}).click();const marker=page.getByRole('dialog',{name:'إضافة مريض'});await marker.getByLabel('الاسم الكامل').fill('سجل ثابت اصطناعي');await marker.getByLabel('رقم الهاتف').fill('+201012345679');await marker.getByRole('button',{name:'حفظ'}).click();await page.getByRole('button',{name:'إضافة مريض'}).click();const invalid=page.getByRole('dialog',{name:'إضافة مريض'});await invalid.getByLabel('الاسم الكامل').fill('اختبار');await invalid.getByLabel('رقم الهاتف').fill('abcde');await invalid.getByRole('button',{name:'حفظ'}).click();await invalid.getByText('اكتب رقم هاتف صحيحاً').waitFor();await invalid.getByRole('button',{name:'إلغاء'}).click();
 await page.evaluate(async()=>{for(let i=0;i<11;i++){const csrf=await (await fetch('/api/auth/csrf')).json();const response=await fetch('/api/patients',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf.csrf_token},body:JSON.stringify({full_name:'سجل اصطناعي '+i,phone:'+2010999'+String(i).padStart(5,'0')})});if(!response.ok)throw Error('fixture create '+response.status)}});
 await page.getByLabel('ابحث بالاسم أو رقم الهاتف').fill('');await page.getByRole('button',{name:'بحث'}).click();await page.getByRole('button',{name:'التالي'}).click();await page.getByText('صفحة 2').waitFor();await page.setViewportSize({width:390,height:844});await page.getByRole('button',{name:'فتح القائمة'}).click();await page.getByRole('link',{name:'المرضى'}).waitFor();await page.getByRole('button',{name:'إغلاق القائمة'}).first().click();
 await page.getByRole('button',{name:'تسجيل الخروج'}).click();await page.getByRole('heading',{name:'مرحباً بعودتك'}).waitFor()
 await signIn('synthetic.doctor');await page.getByText('مساحة الطبيب').waitFor();await page.reload();await page.getByText('مساحة الطبيب').waitFor()
 if(errors.length)throw Error('browser console errors: '+errors.join(' | '))
 console.log('PASS browser: anonymous 401, invalid password, reception and doctor nav, create/search/details/edit/archive, validation, pagination, mobile menu, logout, refresh, RTL, console')
}catch(e){console.error(e);process.exitCode=1}finally{await browser.close()}
