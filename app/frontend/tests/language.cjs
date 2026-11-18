const {chromium}=require('playwright-core');
const base=process.env.TIL_E2E_BASE_URL, browserPath=process.env.TIL_BROWSER_PATH;
if(!base||!browserPath)throw Error('Set TIL_E2E_BASE_URL and TIL_BROWSER_PATH.');
const url=new URL(base);
if(url.protocol!=='http:'||!['127.0.0.1','localhost'].includes(url.hostname))throw Error('Test server must be local.');
(async()=>{
 const browser=await chromium.launch({executablePath:browserPath,headless:true,args:['--no-sandbox']});
 try{
  for(const [locale,expected] of [['ru-RU','ru-uz'],['uz-UZ','uz-ru'],['en-US','uz-ru']]){
   const context=await browser.newContext({locale});const page=await context.newPage();
   await page.goto(base);const select=page.getByLabel('Interface language / Til');await select.waitFor();
   if(await select.inputValue()!==expected)throw Error(`${locale} did not select ${expected}`);
   if(await page.locator('html').getAttribute('lang')!==(expected==='ru-uz'?'ru':'uz'))throw Error(`${locale} has the wrong document language`);
   await select.selectOption(expected==='ru-uz'?'uz-ru':'ru-uz');await page.reload();
   if(await select.inputValue()==expected)throw Error(`${locale} did not retain the visitor's explicit choice`);
   await context.close();
  }
  console.log('Language: Russian devices use Russian, others use Uzbek, and visitor choices persist.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
