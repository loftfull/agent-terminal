/* Project message library. No upstream source copied. */
(function(root){
'use strict';
const schema='fix-message-favorites/v1',key='fix.message-favorites.v1';
function clean(item){
 if(!item||typeof item.text!=='string'||!item.text.length||item.text.length>500000)throw Error('Некорректный или слишком большой текст');
 const out={text:item.text};
 for(const k of ['project_id','project_name','session_id','message_id','revision','date']){
  if(typeof item[k]!=='string'||item[k].length>2000)throw Error('Некорректные сведения об источнике');out[k]=item[k];
 }
 return out;
}
function identity(item){return JSON.stringify([item.project_id,item.session_id,item.message_id,item.revision,item.text]);}
function merge(current,incoming){const map=new Map();for(const item of [...current,...incoming]){const c=clean(item);map.set(identity(c),c)}const out=[...map.values()];if(out.length>200||JSON.stringify(out).length>2000000)throw Error('Лимит избранного: 200 сообщений / 2 млн символов');return out;}
function parse(text){if(text.length>2100000)throw Error('Файл слишком большой');const d=JSON.parse(text);if(d.schema!==schema||!Array.isArray(d.items))throw Error('Неизвестный формат избранного');return merge([],d.items);}
function encode(items){return JSON.stringify({schema,items:merge([],items)},null,2);}
function messages(state){return (state.events||[]).filter(e=>e.event_type==='message_record'&&e.author==='user'&&typeof e.text==='string').map(e=>({text:e.text,project_id:String(state.project?.project_id||''),project_name:String(state.project?.name||''),session_id:String(e.session_id||''),message_id:String(e.source_locator?.message_id||e.event_id||''),revision:String(e.revision_hash||e.event_id||''),date:String(e.occurred_at||'Дата сообщения неизвестна')}));}
const api={schema,key,clean,identity,merge,parse,encode,messages};
if(typeof module==='object'&&module.exports)module.exports=api;else root.FixMessages=api;
})(typeof window==='object'?window:globalThis);
