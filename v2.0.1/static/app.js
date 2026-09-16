(() => {
  'use strict';
  const faDigits = '۰۱۲۳۴۵۶۷۸۹';
  const arDigits = '٠١٢٣٤٥٦٧٨٩';
  const months = ['فروردین','اردیبهشت','خرداد','تیر','مرداد','شهریور','مهر','آبان','آذر','دی','بهمن','اسفند'];
  const weekdays = ['ش','ی','د','س','چ','پ','ج'];
  const toAscii = value => String(value ?? '')
    .replace(/[۰-۹]/g, c => String(faDigits.indexOf(c)))
    .replace(/[٠-٩]/g, c => String(arDigits.indexOf(c)));
  const toFa = value => String(value).replace(/\d/g, c => faDigits[Number(c)]);
  const div = (a,b) => Math.floor(a/b);

  function j2g(jy,jm,jd){
    const gdm=[31,28,31,30,31,30,31,31,30,31,30,31];
    jy-=979; jm-=1; jd-=1;
    let jdn=365*jy+div(jy,33)*8+div((jy%33)+3,4);
    for(let i=0;i<jm;i++) jdn+=i<6?31:30;
    jdn+=jd; let gdn=jdn+79;
    let gy=1600+400*div(gdn,146097); gdn%=146097; let leap=true;
    if(gdn>=36525){gdn--;gy+=100*div(gdn,36524);gdn%=36524;if(gdn>=365)gdn++;else leap=false;}
    gy+=4*div(gdn,1461);gdn%=1461;
    if(gdn>=366){leap=false;gdn--;gy+=div(gdn,365);gdn%=365;}
    let gm=0;
    while(gm<12){const len=gdm[gm]+(gm===1&&leap?1:0);if(gdn<len)break;gdn-=len;gm++;}
    return [gy,gm+1,gdn+1];
  }
  function g2j(gy,gm,gd){
    const gdm=[31,28,31,30,31,30,31,31,30,31,30,31];
    gy-=1600;gm--;gd--;
    let gdn=365*gy+div(gy+3,4)-div(gy+99,100)+div(gy+399,400);
    for(let i=0;i<gm;i++)gdn+=gdm[i];
    if(gm>1&&((gy%4===0&&gy%100!==0)||gy%400===0))gdn++;
    gdn+=gd;let jdn=gdn-79;const cycles=div(jdn,12053);jdn%=12053;
    let jy=979+33*cycles+4*div(jdn,1461);jdn%=1461;
    if(jdn>=366){jy+=div(jdn-1,365);jdn=(jdn-1)%365;}
    if(jdn<186)return [jy,1+div(jdn,31),1+jdn%31];
    jdn-=186;return [jy,7+div(jdn,30),1+jdn%30];
  }
  function monthLength(jy,jm){
    if(jm<=6)return 31;if(jm<=11)return 30;
    const g=j2g(jy,12,30), back=g2j(...g);return back[0]===jy&&back[1]===12&&back[2]===30?30:29;
  }
  function parse(value){
    const m=toAscii(value).trim().match(/^(\d{4})\s*[\/\-.]\s*(\d{1,2})\s*[\/\-.]\s*(\d{1,2})$/);
    if(!m)return null;const result=m.slice(1).map(Number);
    if(result[1]<1||result[1]>12||result[2]<1||result[2]>monthLength(result[0],result[1]))return null;
    return result;
  }
  function format(jy,jm,jd){return toFa(`${jy}/${String(jm).padStart(2,'0')}/${String(jd).padStart(2,'0')}`);}

  let activeInput=null, view=null;
  const popup=document.createElement('div');popup.className='jalali-picker shadow';popup.hidden=true;document.body.appendChild(popup);
  function today(){const n=new Date();return g2j(n.getFullYear(),n.getMonth()+1,n.getDate());}
  function position(){if(!activeInput||popup.hidden)return;const r=activeInput.getBoundingClientRect();popup.style.top=`${window.scrollY+r.bottom+6}px`;popup.style.left=`${Math.max(8,Math.min(window.scrollX+r.left,window.scrollX+window.innerWidth-310))}px`;}
  function changeMonth(delta){view[1]+=delta;if(view[1]<1){view[1]=12;view[0]--;}if(view[1]>12){view[1]=1;view[0]++;}render();}
  function render(){
    if(!view)return;const [jy,jm]=view, selected=parse(activeInput.value), firstG=j2g(jy,jm,1);
    const firstWeek=(new Date(firstG[0],firstG[1]-1,firstG[2]).getDay()+1)%7;
    popup.innerHTML='';
    const header=document.createElement('div');header.className='jp-header';
    const prev=document.createElement('button');prev.type='button';prev.className='btn btn-sm btn-light';prev.textContent='‹';prev.onclick=()=>changeMonth(-1);
    const title=document.createElement('div');title.className='fw-bold';title.textContent=`${months[jm-1]} ${toFa(jy)}`;
    const next=document.createElement('button');next.type='button';next.className='btn btn-sm btn-light';next.textContent='›';next.onclick=()=>changeMonth(1);
    header.append(prev,title,next);popup.appendChild(header);
    const week=document.createElement('div');week.className='jp-grid jp-week';weekdays.forEach(x=>{const e=document.createElement('span');e.textContent=x;week.appendChild(e);});popup.appendChild(week);
    const grid=document.createElement('div');grid.className='jp-grid';for(let i=0;i<firstWeek;i++)grid.appendChild(document.createElement('span'));
    const now=today();for(let d=1;d<=monthLength(jy,jm);d++){const b=document.createElement('button');b.type='button';b.textContent=toFa(d);b.className='jp-day';if(selected&&selected[0]===jy&&selected[1]===jm&&selected[2]===d)b.classList.add('selected');if(now[0]===jy&&now[1]===jm&&now[2]===d)b.classList.add('today');b.onclick=()=>{activeInput.value=format(jy,jm,d);activeInput.dispatchEvent(new Event('change',{bubbles:true}));close();};grid.appendChild(b);}popup.appendChild(grid);
    const footer=document.createElement('div');footer.className='jp-footer';
    const nowBtn=document.createElement('button');nowBtn.type='button';nowBtn.className='btn btn-sm btn-outline-primary';nowBtn.textContent='امروز';nowBtn.onclick=()=>{const x=today();activeInput.value=format(...x);activeInput.dispatchEvent(new Event('change',{bubbles:true}));close();};
    const clear=document.createElement('button');clear.type='button';clear.className='btn btn-sm btn-outline-secondary';clear.textContent='پاک کردن';clear.onclick=()=>{activeInput.value='';activeInput.dispatchEvent(new Event('change',{bubbles:true}));close();};footer.append(nowBtn,clear);popup.appendChild(footer);position();
  }
  function open(input){activeInput=input;view=parse(input.value)||today();popup.hidden=false;render();}
  function close(){popup.hidden=true;activeInput=null;}

  function initJalali(root=document){root.querySelectorAll('.jalali-date:not([data-jalali-ready])').forEach(input=>{
    input.dataset.jalaliReady='1';input.setAttribute('placeholder','۱۴۰۵/۰۶/۰۶');input.setAttribute('autocomplete','off');input.setAttribute('inputmode','numeric');
    input.addEventListener('focus',()=>open(input));input.addEventListener('click',()=>open(input));
    const validate=()=>{const bad=Boolean(input.value&&!parse(input.value));input.classList.toggle('is-invalid',bad);input.setCustomValidity(bad?'تاریخ شمسی نامعتبر است. نمونه: ۱۴۰۵/۰۶/۰۶':'');};
    input.addEventListener('input',validate);input.addEventListener('change',validate);input.addEventListener('blur',validate);
  });}
  initJalali();
  document.addEventListener('mousedown',e=>{if(!popup.hidden&&!popup.contains(e.target)&&e.target!==activeInput)close();});
  window.addEventListener('resize',position);window.addEventListener('scroll',position,true);

  document.querySelectorAll('.money-input').forEach(input=>{
    const formatMoney=()=>{let digits=toAscii(input.value).replace(/[^0-9]/g,'').replace(/^0+(?=\d)/,'');if(!digits){input.value='';return;}input.value=toFa(digits.replace(/\B(?=(\d{3})+(?!\d))/g,'٬'));};
    input.addEventListener('input',formatMoney);formatMoney();
  });

  window.AppJalali={init:initJalali,parse,format};
  window.AppNumbers={toAscii,toFa,formatInteger(value){const n=Math.round(Number(value)||0);return toFa(String(n).replace(/\B(?=(\d{3})+(?!\d))/g,'٬'));}};
})();
