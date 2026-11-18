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
   const result=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21a','wcag21aa']).analyze();
   console.log(`${screen}: ${result.violations.length} automated violations`);
   for(const issue of result.violations){failed=true;console.error(`${issue.id}: ${issue.nodes.map(n=>n.target.join(' ')).join(', ')}`)}
  }
 }finally{await browser.close()}
 if(failed)process.exitCode=1;
})().catch(error=>{console.error(error);process.exitCode=1});
