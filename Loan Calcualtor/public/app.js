const $ = id => document.getElementById(id);
const form = $('loan-form');
const money = (n, cents = false) => new Intl.NumberFormat('en-AU', {style:'currency',currency:'AUD',maximumFractionDigits:cents?2:0}).format(n);
const duration = n => `${Math.floor(n/12)}y ${n%12}m`;
let kind = 'home', latest, timer, requestId = 0, bankRequestId = 0;
const field = name => form.elements.namedItem(name);
function setText(id, value) { $(id).textContent = value; }
function invalidate() {
  latest = null;
  $('download').disabled = true;
  for (const id of ['monthly','lvr','interest','total','capacity','time-saved','interest-saved','payoff-time']) setText(id, '—');
  setText('capacity-detail','Update valid inputs to see an estimate.');
  $('chart').replaceChildren();
}
async function update() {
  const id = ++requestId;
  clearTimeout(timer);
  if (!form.checkValidity()) { invalidate(); setText('form-error','Please check the input values.'); return; }
  setText('form-error','');
  document.querySelector('.results').setAttribute('aria-busy','true');
  const data = Object.fromEntries(new FormData(form)); data.kind = kind;
  try {
    const response = await fetch('/api/calculate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
    const result = await response.json();
    if (id !== requestId) return;
    if (!response.ok) throw new Error(result.error);
    latest = result; $('download').disabled = false;
    setText('loan-amount',money(result.principal));
    setText('deposit-percent',`${(100-result.lvr).toFixed(1)}% deposit`);
    setText('monthly',money(result.monthly,true));
    setText('lvr',`${result.lvr.toFixed(1)}%`);
    setText('interest',money(result.totalInterest)); setText('total',money(result.totalPaid));
    setText('capacity',money(result.capacity));
    setText('capacity-detail',`${result.lendingPercent.toFixed(1)}% estimated lending · assessed at ${result.assessmentRate.toFixed(2)}% p.a. · ${result.shortfall > 0 ? money(result.shortfall)+' above modelled capacity' : 'Requested loan is within modelled capacity'}. This is not approval.`);
    setText('extra-copy',money(Number(data.extra)));
    setText('time-saved',duration(result.monthsSaved));setText('interest-saved',money(result.interestSaved));setText('payoff-time',duration(result.payoffMonths));
    drawChart(result);
  } catch(e) { if(id===requestId){invalidate();setText('form-error',e.message || 'Unable to calculate. Check the server is running.');} }
  finally { if(id===requestId) document.querySelector('.results').setAttribute('aria-busy','false'); }
}
function svgElement(name, attrs, text) {
  const el = document.createElementNS('http://www.w3.org/2000/svg',name);
  for(const [k,v] of Object.entries(attrs)) el.setAttribute(k,v);
  if(text!==undefined) el.textContent=text;
  return el;
}
function drawChart(r) {
  const svg = $('chart');svg.replaceChildren();
  svg.append(svgElement('title',{},`Loan balance: standard term ${duration(r.base.length)}, with extra payments ${duration(r.payoffMonths)}. Interest saved ${money(r.interestSaved)}.`));
  const x = m => 58+m/r.base.length*584, y = b => 202-b/r.principal*174;
  for(let i=0;i<=4;i++) {
    const balance=r.principal*i/4;
    svg.append(svgElement('line',{x1:58,y1:y(balance),x2:642,y2:y(balance),stroke:'#e9ede4','stroke-dasharray':'3 5'}));
    svg.append(svgElement('text',{x:46,y:y(balance)+4,'text-anchor':'end',fill:'#939f89','font-size':10},balance>=1000000?`$${(balance/1000000).toFixed(1)}m`:`$${Math.round(balance/1000)}k`));
  }
  for(let i=0;i<=6;i++) svg.append(svgElement('text',{x:x(r.base.length*i/6),y:228,'text-anchor':'middle',fill:'#939f89','font-size':10},(r.base.length*i/72).toFixed(0)));
  const points = rows => [[0,r.principal],...rows.map(v=>[v.month,v.balance])].map(([m,b])=>`${x(m)},${y(b)}`).join(' ');
  svg.append(svgElement('polygon',{points:`${x(0)},202 ${points(r.accelerated)} ${x(r.payoffMonths)},202`,fill:'#eef4e6'}));
  svg.append(svgElement('polyline',{points:points(r.base),fill:'none',stroke:'#bbc7b0','stroke-width':2.5,'stroke-dasharray':'5 4'}));
  svg.append(svgElement('polyline',{points:points(r.accelerated),fill:'none',stroke:'#658b49','stroke-width':3}));
  svg.append(svgElement('circle',{cx:x(r.payoffMonths),cy:202,r:4,fill:'#658b49'}));
}
form.addEventListener('submit',e=>{e.preventDefault();update();});
form.addEventListener('input',e=>{
  ++requestId; invalidate();
  if(e.target.name==='rate') setText('rate-origin','Custom rate entered. Confirm current pricing with your lender.');
  if(e.target.name==='extra') $('extra-range').value=Math.min(5000,Number(e.target.value));
  clearTimeout(timer);timer=setTimeout(update,250);
});
$('extra-range').addEventListener('input',e=>{field('extra').value=e.target.value;});
document.querySelectorAll('[data-kind]').forEach(button=>button.addEventListener('click',()=>{
  kind=button.dataset.kind;
  document.querySelectorAll('[data-kind]').forEach(b=>{b.classList.toggle('active',b===button);b.setAttribute('aria-pressed',b===button);});
  const commercial=kind==='commercial';
  $('commercial-fields').hidden=!commercial;
  field('lvrCap').value=commercial?65:80;field('years').value=commercial?20:30;field('rate').value=commercial?8:6;
  setText('rate-origin','Illustrative rate. Enter your quote or explore bank rates below.');
  setText('income-label',commercial?'Monthly business cash inflow after tax':'Monthly income after tax');
  setText('expense-label',commercial?'Operating costs / month':'Living expenses / month');
  setText('income-help',commercial?'Use sustainable business cash inflows and operating costs. Coverage ratio defaults to an illustrative 1.25.':'Use combined monthly take-home income and household costs.');
  ++bankRequestId; $('bank-products').replaceChildren(); $('fetch-banks').disabled=false;
  setText('bank-status','Loan type changed. Retrieve products for this loan type.');update();
}));
$('download').addEventListener('click',()=>{
  if(!latest)return;
  const rows=['scenario,month,payment,principal,interest,balance'];
  for(const [label,schedule] of [['minimum',latest.base],['extra',latest.accelerated]]) for(const r of schedule) rows.push([label,r.month,...['payment','principal','interest','balance'].map(k=>r[k].toFixed(2))].join(','));
  const url=URL.createObjectURL(new Blob([rows.join('\r\n')],{type:'text/csv'}));
  const a=document.createElement('a');a.href=url;a.download='loanleaf-repayment-schedule.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
});
function element(tag, text, className) {const e=document.createElement(tag); if(text)e.textContent=text;if(className)e.className=className;return e;}
function safeLink(url,text) {
  const a=element('a',text);try{const u=new URL(url);if(u.protocol==='https:'){a.href=u.href;a.target='_blank';a.rel='noopener noreferrer';}}catch{} return a;
}
$('fetch-banks').addEventListener('click',async()=>{
  const id=++bankRequestId;
  $('fetch-banks').disabled=true;$('bank-products').replaceChildren();setText('bank-status','Retrieving published bank products and rate conditions…');
  try {
    const response=await fetch(`/api/banks?bank=${encodeURIComponent($('bank').value)}&kind=${kind}`);
    const data=await response.json();if(id!==bankRequestId)return;if(!response.ok)throw new Error(data.error);
    setText('bank-status',`${data.bank} · retrieved ${new Date(data.fetchedAt).toLocaleString('en-AU')} · ${data.products.length} products. ${data.failed?data.failed+' product details could not be retrieved. ':''}Published rates are conditional and are not matched to your circumstances.`);
    if(!data.products.length){$('bank-products').append(element('p','No products available from this feed. Contact the lender for a quote.'));}
    for(const product of data.products){
      const card=element('article',null,'bank-product');card.append(element('h3',`${product.brand} · ${product.name}`));
      card.append(safeLink(product.source,'View lender product information ↗'));
      if(!product.rates.length)card.append(element('p','No supported principal-and-interest base rate published. Request a lender quote.'));
      for(const rate of product.rates){
        const pct=Number(rate.rate)*100;if(!Number.isFinite(pct)||pct<=0||pct>30)continue;
        const row=element('div',null,'rate-row');
        row.append(element('span',`${pct.toFixed(2)}% p.a. · ${rate.lendingRateType.toLowerCase()} · ${(rate.loanPurpose||'purpose unspecified').replaceAll('_',' ').toLowerCase()}`));
        const use=element('button','Use in scenario');use.type='button';use.addEventListener('click',()=>{field('rate').value=pct.toFixed(2);setText('rate-origin',`${product.brand}: ${product.name}. Published rate, not an offer. Check conditions below; rate held constant for modelling.`);update();$('calculator').scrollIntoView({behavior:'smooth'});});row.append(use);card.append(row);
        const details=element('details');details.append(element('summary','Rate conditions and tiers'));details.append(element('pre',JSON.stringify(rate,null,2)));card.append(details);
      }
      const details=element('details');details.append(element('summary','Product constraints, fees and source'));details.append(element('pre',JSON.stringify({updated:product.updated,constraints:product.constraints,fees:product.fees},null,2)));details.append(safeLink(product.apiSource,'View source data ↗'));card.append(details);$('bank-products').append(card);
    }
  }catch(e){if(id===bankRequestId)setText('bank-status',e.message||'Unable to connect to bank feed. Enter a quoted rate manually.');}
  finally{if(id===bankRequestId)$('fetch-banks').disabled=false;}
});
update();
