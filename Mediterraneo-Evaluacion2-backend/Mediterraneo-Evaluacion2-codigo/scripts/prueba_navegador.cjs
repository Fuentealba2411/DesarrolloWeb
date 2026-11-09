// Comprobación opcional: npm install playwright; npx playwright install chromium.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const https = require('https');
const root = path.resolve(__dirname, '..');
const runtime = process.env.RUNTIME_DIR || path.join(root, '.runtime');
const ca = fs.readFileSync(path.join(runtime, 'cert.pem'));
function provider(url, method='GET') {
  return new Promise((resolve,reject) => {
    const req = https.request('https://127.0.0.1:8507'+url, {method,ca,headers:{'X-Service-Key':fs.readFileSync(path.join(runtime,'operator.token'),'utf8')}}, res=>{
      let s='';res.on('data',c=>s+=c);res.on('end',()=>res.statusCode===200?resolve(JSON.parse(s)):reject(new Error('Proveedor: '+res.statusCode)));
    });req.on('error',reject);req.end();
  });
}
(async()=>{
  const browser = await chromium.launch({executablePath:process.env.BROWSER_EXECUTABLE || undefined,headless:true,args:process.env.BROWSER_SINGLE_PROCESS ? ['--no-sandbox','--single-process','--no-zygote','--in-process-gpu'] : ['--no-sandbox']});
  const context = await browser.newContext({ignoreHTTPSErrors:true});
  const page = await context.newPage(); const errors=[];const evidence=[];
  page.on('pageerror',e=>errors.push(e.message));
  try {
    for(const width of [375,768,1024,1440]) {
      await page.setViewportSize({width,height:1000});
      for(const name of ['index.html','menu.html','promociones.html','contacto.html','reserva.html','cuenta.html','pedido.html','gestion.html']) {
        await page.goto('https://localhost:8443/'+name);
        if(name==='menu.html') await page.locator('#listaPlatos .plato').first().waitFor();
        const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1);
        if(overflow) { console.log(await page.evaluate(()=>[...document.querySelectorAll('main *')].filter(e=>e.getBoundingClientRect().right>innerWidth+1).map(e=>({tag:e.tagName,clase:e.className})).slice(0,8)));throw new Error('Desborde: '+name+' a '+width); }
        evidence.push({pantalla:name,ancho:width,desborde:false});
      }
    }
    await page.setViewportSize({width:1440,height:1000});
    await page.goto('https://localhost:8443/cuenta.html');
    const email='navegador-'+Date.now()+'@example.test';
    const fields={nombre:'Persona Ficticia',correo:email,clave:'Prueba-academica-2026',run:'11111111-1',direccion:'Direccion ficticia 123',comuna:'Santiago',provincia:'Santiago',region:'Metropolitana',nacimiento:'1990-01-01',telefono:'+56911111111'};
    for(const [n,v] of Object.entries(fields))await page.locator('#reg_'+n).fill(v);
    await page.locator('#registro button').click();
    await page.waitForFunction(()=>document.querySelector('#avisoGlobal')?.textContent.includes('Registro creado'));
    const mails=await provider('/operator/mailbox');
    const code=mails.find(x=>x.recipient===email).body.split(': ').at(-1);
    await page.locator('#codigo').fill(code);await page.locator('#verificacion button[type=submit], #verificacion button:not([type])').click();
    await page.waitForFunction(()=>document.querySelector('#avisoGlobal')?.textContent.includes('Correo verificado'));
    await page.locator('[aria-label="Perfil"]').click();
    await page.locator('#correoAcceso').fill(email);await page.locator('#claveAcceso').fill(fields.clave);
    await page.locator('#formularioAcceso button[type=submit]').click();
    await page.waitForFunction(()=>document.querySelector('#estadoCuenta')?.textContent.includes('Cuenta:'));
    await page.goto('https://localhost:8443/menu.html');
    await page.getByRole('button',{name:'Agregar Moussaka al carrito',exact:true}).click();
    await page.goto('https://localhost:8443/pedido.html');
    await page.locator('#direccionPedido').fill(fields.direccion);await page.locator('#pedido button').click();
    await page.waitForFunction(()=>document.querySelector('#resultadoPedido')?.textContent.includes('Total oficial:'));
    await page.goto('https://localhost:8443/cuenta.html');
    await page.getByRole('button',{name:'Iniciar pago de prueba',exact:true}).click();
    await page.waitForFunction(()=>document.querySelector('#avisoGlobal')?.textContent.includes('Pago iniciado'));
    const text=await page.locator('#avisoGlobal').textContent();const id=text.match(/[0-9a-f]{8}-[0-9a-f-]{27,}/)[0];
    await provider('/operator/approve/'+id,'POST');
    await page.locator('#recargar').click();await page.waitForFunction(()=>document.querySelector('#pedidos')?.textContent.includes('pagado'));
    await page.getByRole('button',{name:'Ver comprobante',exact:true}).click();
    await page.locator('#pedidos .comprobante').waitFor();
    const qa=path.join(root,'tmp');fs.mkdirSync(qa,{recursive:true});
    await page.screenshot({path:path.join(qa,'cuenta-verificada.png'),fullPage:true});
    await page.goto('https://localhost:8443/menu.html');await page.locator('#listaPlatos .plato').first().waitFor();
    await page.screenshot({path:path.join(qa,'menu-escritorio.png'),fullPage:true});
    await page.setViewportSize({width:375,height:900});await page.screenshot({path:path.join(qa,'menu-movil.png'),fullPage:true});
    evidence.push({flujo:'registro -> correo sandbox -> sesión -> catálogo -> pedido -> pago sandbox -> comprobante',resultado:'correcto'});
    if(errors.length)throw new Error('Errores JavaScript: '+errors.join('; '));
    fs.writeFileSync(path.join(root,'docs','resultados-navegador.json'),JSON.stringify({checks:evidence,erroresJavaScript:errors},null,2));
    console.log('Navegador: 32 comprobaciones responsivas y compra completa correctas.');
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
