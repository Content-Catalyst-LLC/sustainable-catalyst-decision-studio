(function(){"use strict";
const VERSION='1.16.0';
const DB_NAME='scds-offline-workspace';
const STORE='drafts';
const FALLBACK_KEY='scds_offline_draft_v1_16_0';
const SENSITIVE=/api[_-]?key|secret|password|token|authorization|cookie|private[_-]?key/i;
const AUTOMATIC_WRITE_REPLAY=false;
function all(root,selector){return Array.from(root.querySelectorAll(selector))}
function strip(value){if(Array.isArray(value))return value.map(strip);if(value&&typeof value==='object'){const out={};Object.keys(value).forEach(key=>{out[key]=SENSITIVE.test(key)?'[removed]':strip(value[key])});return out}return value}
function collect(root){const fields={};all(root,'[data-scds-field]').forEach(el=>{fields[el.dataset.scdsField]=el.value});return{schema:'scds-offline-workspace/1.0',version:VERSION,saved_at:new Date().toISOString(),packet:strip(root._scdsPacket||{}),fields:fields,online:navigator.onLine}}
function announce(root,message){const el=root.querySelector('[data-scds-offline-status]');if(el)el.textContent=message}
function openDb(){return new Promise((resolve,reject)=>{if(!('indexedDB'in window))return reject(new Error('IndexedDB unavailable'));const req=indexedDB.open(DB_NAME,1);req.onupgradeneeded=()=>{const db=req.result;if(!db.objectStoreNames.contains(STORE))db.createObjectStore(STORE,{keyPath:'id'})};req.onsuccess=()=>resolve(req.result);req.onerror=()=>reject(req.error||new Error('IndexedDB open failed'))})}
function saveIndexed(record){return openDb().then(db=>new Promise((resolve,reject)=>{const tx=db.transaction(STORE,'readwrite');tx.objectStore(STORE).put(Object.assign({id:'active'},record));tx.oncomplete=()=>{db.close();resolve(record)};tx.onerror=()=>{db.close();reject(tx.error||new Error('IndexedDB save failed'))}}))}
function save(root){const record=collect(root);return saveIndexed(record).catch(()=>{localStorage.setItem(FALLBACK_KEY,JSON.stringify(record));return record}).then(()=>announce(root,(navigator.onLine?'Online':'Offline')+' · local draft saved '+new Date().toLocaleTimeString()))}
function load(){return openDb().then(db=>new Promise((resolve,reject)=>{const tx=db.transaction(STORE,'readonly');const req=tx.objectStore(STORE).get('active');req.onsuccess=()=>{db.close();resolve(req.result||null)};req.onerror=()=>{db.close();reject(req.error)}})).catch(()=>{try{return JSON.parse(localStorage.getItem(FALLBACK_KEY)||'null')}catch(e){return null}})}
function init(root){let timer=null;const schedule=()=>{clearTimeout(timer);timer=setTimeout(()=>save(root),1200)};root.addEventListener('input',schedule,{passive:true});root.addEventListener('change',schedule,{passive:true});window.addEventListener('online',()=>{announce(root,'Online · local draft retained until explicitly replaced.');save(root)});window.addEventListener('offline',()=>announce(root,'Offline · changes will be saved locally; governance, publication handoffs, and institutional APIs require reconnection.'));announce(root,(navigator.onLine?'Online':'Offline')+' · offline draft recovery enabled.');load().then(record=>{if(record&&record.saved_at)announce(root,(navigator.onLine?'Online':'Offline')+' · recovery draft available from '+new Date(record.saved_at).toLocaleString())});setInterval(()=>save(root),15000)}
document.addEventListener('DOMContentLoaded',()=>all(document,'[data-scds-app]').forEach(init));
})();
