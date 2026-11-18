const {chromium}=require('playwright-core');
const AxeBuilder=require('@axe-core/playwright').default;
const base=process.env.TIL_E2E_BASE_URL, browserPath=process.env.TIL_BROWSER_PATH;
if(!base||!browserPath){console.error('Set TIL_E2E_BASE_URL and TIL_BROWSER_PATH.');process.exit(1)}
const url=new URL(base);
if(url.protocol!=='http:'||!['127.0.0.1','localhost'].includes(url.hostname))throw Error('Test server must be local.');
(async()=>{
 const browser=await chromium.launch({executablePath:browserPath,headless:true,args:['--no-sandbox']});
 const context=await browser.newContext({viewport:{width:390,height:844}});
 const page=await context.newPage();let failed=false;
 try{
  await page.goto(base,{waitUntil:'networkidle'});
  for(const screen of ['home','preview']){
   if(screen==='preview')await page.getByRole('button',{name:/Mashqni sinab ko‘rish/}).click();
   await page.evaluate(() => Promise.all(document.getAnimations().map(animation => animation.finished.catch(() => {}))));
   const result=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21a','wcag21aa']).analyze();
   console.log(`${screen}: ${result.violations.length} automated violations`);
   for(const issue of result.violations){failed=true;console.error(`${issue.id}: ${issue.nodes.map(n=>n.target.join(' ')).join(', ')}`)}
  }
  let release,started;const gate=new Promise(r=>release=r),submitted=new Promise(r=>started=r);
  await page.route('**/api/preview/uz-ru/answer',async route=>{started();await gate;await route.fulfill({status:200,json:{correct:true,explanation:'Old direction'}})});
  await page.getByRole('button',{name:/Привет/}).click();
  await page.getByRole('button',{name:/Tekshirish/}).click();await submitted;
  await page.getByLabel('Interface language / Til').selectOption('ru-uz');
  await page.getByRole('button',{name:/Salom/}).waitFor();
  const oldResponse=page.waitForResponse(response=>response.url().includes('/api/preview/uz-ru/answer'));release();await oldResponse;
  if(await page.getByText('Old direction').count())throw Error('Old feedback leaked into the new course');
  await page.getByRole('button',{name:/Salom/}).click();
  await page.getByRole('button',{name:/Проверить/}).click();
  await page.getByText('Верно!',{exact:true}).waitFor();
  console.log('Guest preview: switching direction during submission passed');
 }finally{await browser.close()}
 if(failed)process.exitCode=1;
})().catch(error=>{console.error(error);process.exitCode=1});
