const {chromium}=require('playwright-core');
const AxeBuilder=require('@axe-core/playwright').default;
const base=process.env.TIL_E2E_BASE_URL;
const browserPath=process.env.TIL_BROWSER_PATH;
if(process.env.TIL_E2E_ISOLATED!=='1'||!base||!browserPath){
 console.error('Set TIL_E2E_ISOLATED=1, TIL_E2E_BASE_URL and TIL_BROWSER_PATH; use a disposable test database.');
 process.exit(1);
}
const url=new URL(base);
if(url.protocol!=='http:'||!['127.0.0.1','localhost'].includes(url.hostname))throw Error('Test server must be local.');
(async()=>{
 const browser=await chromium.launch({executablePath:browserPath,headless:true,args:['--no-sandbox']});
 const context=await browser.newContext({viewport:{width:390,height:844}});const page=await context.newPage();
 try{
  await page.goto(base,{waitUntil:'networkidle'});
  await page.getByRole('button',{name:/O‘rganishni boshlash/}).first().click();
  await page.locator('input[name="name"]').fill('QA');
  await page.locator('input[name="email"]').fill(`qa-${Date.now()}@example.com`);
  await page.locator('input[name="password"]').fill('test-password-123');
  await page.locator('form').getByRole('button',{name:/Hisob yaratish/}).click();
  await page.getByRole('radio',{name:'O‘qish'}).check();
  await page.locator('.onboarding-form').getByRole('button',{name:/O‘rganishni boshlash/}).click();
  async function scan(name){const r=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21a','wcag21aa']).analyze();console.log(name+': '+r.violations.length+' automated violations');if(r.violations.length)throw Error(name+': '+r.violations.map(v=>v.id).join(', '));}
  await scan('dashboard');
  await page.locator('.lesson-row').filter({hasText:'Birinchi sonlar'}).first().click();
  await scan('lesson intro');
  await page.getByRole('button',{name:/Mashqlarni boshlash/}).click();
  await scan('exercise');
 }finally{await browser.close()}
})().catch(e=>{console.error(e.message);process.exitCode=1});
