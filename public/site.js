(function(){
  var b=document.querySelector('.burger'),m=document.getElementById('menu');
  if(b)b.addEventListener('click',function(){var o=m.classList.toggle('open');b.setAttribute('aria-expanded',o)});
  // gallery
  var main=document.getElementById('main');
  document.querySelectorAll('.th').forEach(function(t){t.addEventListener('click',function(){
    main.src=t.dataset.src;document.querySelectorAll('.th').forEach(function(x){x.classList.remove('on')});t.classList.add('on')})});
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
