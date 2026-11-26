(function(){
  var b=document.querySelector('.burger'),m=document.getElementById('menu');
  if(b)b.addEventListener('click',function(){var o=m.classList.toggle('open');b.setAttribute('aria-expanded',o)});
  // gallery
  var sl=document.getElementById('slides');
  if(sl){var ths=[].slice.call(document.querySelectorAll('.th')),n=sl.children.length,dots=document.getElementById('dots');
    for(var i=0;i<n;i++){dots.appendChild(document.createElement('i'))}
    var cur=function(){return Math.round(sl.scrollLeft/sl.clientWidth)};
    var go=function(i){i=(i+n)%n;sl.scrollTo({left:i*sl.clientWidth,behavior:'smooth'})};
    var mark=function(){var c=cur();ths.forEach(function(t,k){t.classList.toggle('on',k===c)});[].forEach.call(dots.children,function(d,k){d.classList.toggle('on',k===c)})};
    sl.addEventListener('scroll',function(){clearTimeout(sl._t);sl._t=setTimeout(mark,60)});
    ths.forEach(function(t,k){t.addEventListener('click',function(){go(k)})});
    document.querySelector('.arr.prev').addEventListener('click',function(){go(cur()-1)});
    document.querySelector('.arr.next').addEventListener('click',function(){go(cur()+1)});
    document.addEventListener('keydown',function(e){if(e.key==='ArrowLeft')go(cur()-1);if(e.key==='ArrowRight')go(cur()+1)});
    mark();}
  // catalog filters
  var grid=document.getElementById('grid');if(!grid)return;
  var cards=[].slice.call(grid.children),cat='all',q=document.getElementById('q'),col=document.getElementById('color'),
      sort=document.getElementById('sort'),inst=document.getElementById('instock'),n=document.getElementById('n'),empty=document.getElementById('empty');
  var params=new URLSearchParams(location.search);if(params.get('cat'))cat=params.get('cat');
  function apply(){
    var s=(q.value||'').toLowerCase().trim(),c=col.value,k=0;
    cards.forEach(function(el){var d=el.dataset,ok=(cat==='all'||d.cat===cat)&&(!c||(' '+d.colors+' ').indexOf(' '+c+' ')>-1)
      &&(!s||d.name.indexOf(s)>-1)&&(!inst.checked||d.status==='instock'||d.status==='few');el.hidden=!ok;if(ok)k++});
    var arr=cards.slice();
    if(sort.value)arr.sort(function(a,b){var d=a.dataset.price-b.dataset.price;return sort.value==='up'?d:-d});
    arr.forEach(function(el){grid.appendChild(el)});
    n.textContent=k;empty.hidden=k>0;
    document.querySelectorAll('.chip').forEach(function(x){x.classList.toggle('on',x.dataset.cat===cat)});
  }
  document.querySelectorAll('.chip').forEach(function(x){x.addEventListener('click',function(){cat=x.dataset.cat;apply()})});
  [q,col,sort,inst].forEach(function(x){x.addEventListener('input',apply);x.addEventListener('change',apply)});
  apply();
})();
/* live prices / stock / sold out from the Google Sheet */
(function(){
  if(!window.MX_SHEET)return;
  function parse(t){var rows=[],row=[],f='',q=false;for(var i=0;i<t.length;i++){var c=t[i];if(q){if(c=='"'&&t[i+1]=='"'){f+='"';i++}else if(c=='"')q=false;else f+=c}else if(c=='"')q=true;else if(c==','){row.push(f);f=''}else if(c=='\n'){row.push(f);rows.push(row);row=[];f=''}else if(c!='\r')f+=c}if(f||row.length){row.push(f);rows.push(row)}return rows}
  function num(v){v=String(v||'').replace(/[^\d]/g,'');return v?parseInt(v,10):null}
  var T=window.MX_T||{};
  fetch(window.MX_SHEET,{cache:'no-store'}).then(function(r){return r.text()}).then(function(txt){
    var rows=parse(txt),h=rows.shift().map(function(x){return x.trim().toLowerCase()}),data={};
    var ci=function(k){for(var i=0;i<h.length;i++)if(h[i].indexOf(k)===0)return i;return -1};
    var iS=ci('code'),iP=ci('price'),iQ=ci('stock'),iX=ci('sold');
    rows.forEach(function(r){var s=(r[iS]||'').trim();if(!s)return;var p=num(r[iP]),q=String(r[iQ]||'').trim(),x=/^(y|yes|այո|да|x|1|true)/i.test((r[iX]||'').trim());
      var qn=/^\d[\d\s.,]*$/.test(q)?num(q):null;var st;if(x||qn===0)st='sold';else if(qn!==null)st=qn<=5?'few':'instock';else if(!q)st='ask';else if(/last|few|посл|վերջ/i.test(q))st='few';else if(/sold|прод|վաճառ/i.test(q))st='sold';else if(/ask|уточ|հարց/i.test(q))st='ask';else st='instock';data[s]={p:p,st:st}});
    var fmt=function(p){return p.toLocaleString('en-US').replace(/,/g,' ')+' '+(T.amd||'AMD')};
    document.querySelectorAll('.card[data-slug]').forEach(function(c){var d=data[c.dataset.slug];if(!d)return;
      if(d.p){c.dataset.price=d.p;var pe=c.querySelector('.price');if(pe)pe.textContent=fmt(d.p)}
      c.dataset.status=d.st;c.classList.toggle('is-sold',d.st==='sold');
      var b=c.querySelector('.badge');if(b)b.remove();
      if(d.st==='few'||d.st==='sold'){b=document.createElement('span');b.className='badge b-'+d.st;b.textContent=T[d.st];c.querySelector('.card-img').appendChild(b)}});
    var bp=document.querySelector('.big-price[data-slug]');
    if(bp){var d=data[bp.dataset.slug];if(d){if(d.p)bp.textContent=fmt(d.p);var b=document.querySelector('.info>.badge');if(b){b.className='badge b-'+d.st;b.textContent=T[d.st]}var a=document.getElementById('avail');if(a)a.textContent=T[d.st]}}
    var g=document.getElementById('grid');if(g&&g.dispatchEvent)document.getElementById('instock')&&document.getElementById('instock').dispatchEvent(new Event('change'));
  }).catch(function(){});
})();
