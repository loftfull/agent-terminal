/* Bounded local cache. Canonical project memory is never written here. */
const RepositoryCache=(()=>{
 const prefix='agent-terminal.github-snapshot.v1:';
 function validate(value){
  if(!value||value.schema!=='github-project-observation/v1'||typeof value.repository!=='string'||!value.metadata||!value.sections||Array.isArray(value.sections)||value.continuous_ingestion!==false)throw Error('Неверный формат GitHub-снимка');
  if(!/^[A-Za-z0-9][A-Za-z0-9-]{0,38}\/[A-Za-z0-9_.-]{1,100}$/.test(value.repository)||value.repository.split('/')[1]==='..')throw Error('Неверный репозиторий');
  if(typeof value.observed_at!=='string'||!Number.isFinite(Date.parse(value.observed_at)))throw Error('Нет даты наблюдения');
  if(value.metadata.full_name?.toLowerCase()!==value.repository.toLowerCase())throw Error('Идентичность репозитория не совпадает');
  const names=['commits','issues','pulls','releases','actions','languages','readme'];
  if(names.some(name=>!Object.hasOwn(value.sections,name)))throw Error('Неполный пакет разделов');
  for(const [name,section] of Object.entries(value.sections)){
   if(!names.includes(name)||!section||!['observed','unavailable'].includes(section.status))throw Error('Неверный раздел снимка');
   if(section.status==='observed'){const data=section.data;if(['commits','issues','pulls','releases'].includes(name)&&!Array.isArray(data))throw Error('Неверный список записей');if(name==='actions'&&!Array.isArray(data?.workflow_runs))throw Error('Неверный список CI');if(['languages','readme'].includes(name)&&(!data||typeof data!=='object'||Array.isArray(data)))throw Error('Неверное содержимое раздела')}
   const u=new URL(section.source);
   if(u.origin!=='https://api.github.com'||u.username||u.password||!u.pathname.toLowerCase().startsWith('/repos/'+value.repository.toLowerCase()+'/'))throw Error('Источник другого репозитория');
  }
  const text=JSON.stringify(value);if(text.length>500000)throw Error('Снимок слишком большой для браузерного кэша. Скачайте JSON.');return text;
 }
 function key(value){return prefix+encodeURIComponent(value.repository.toLowerCase())+':'+encodeURIComponent(new Date(value.observed_at).toISOString())}
 function list(storage){
  const items=[],warnings=[];let size=0,count=0;
  for(let i=0;i<storage.length;i++){
   const k=storage.key(i);if(!k?.startsWith(prefix))continue;
   if(++count>100){warnings.push('Слишком много записей кэша; показаны первые 100.');break}
   try{const text=storage.getItem(k);if(!text||text.length>500000)throw Error('Размер записи недопустим');size+=text.length;const value=JSON.parse(text);validate(value);if(key(value)!==k)throw Error('Ключ снимка не совпадает');items.push(value)}catch(e){warnings.push('Повреждённый снимок пропущен: '+e.message)}
  }
  return {items:items.sort((a,b)=>Date.parse(b.observed_at)-Date.parse(a.observed_at)),warnings,size,count};
 }
 function save(storage,value){
  const text=validate(value),k=key(value),old=storage.getItem(k);
  if(old!==null){if(old!==text)throw Error('Снимок с этой датой уже сохранён и отличается. Существующий снимок не заменён.');return {added:false}}
  const current=list(storage);if(current.count>=20||current.size+text.length>2000000)throw Error('Кэш заполнен. Скачайте JSON; прежние снимки сохранены.');
  storage.setItem(k,text);return {added:true};
 }
 function remove(storage,value){validate(value);storage.removeItem(key(value))}
 return {list,save,remove,validate,prefix};
})();
if(typeof module!=='undefined')module.exports=RepositoryCache;
