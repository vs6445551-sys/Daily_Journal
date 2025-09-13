// Unified frontend logic for login, signup and app pages.

function showToast(msg, timeout=3000){
  const t = document.getElementById('toast');
  if(!t) return alert(msg);
  t.textContent = msg; t.classList.add('show');
  setTimeout(()=> t.classList.remove('show'), timeout);
}

async function postJson(url, data){
  const res = await fetch(url, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(data)});
  const json = await res.json().catch(()=>({success:false,error:'Invalid response'}));
  if(!res.ok && json && json.error) throw new Error(json.error);
  return json;
}

// --- Login page ---
const loginForm = document.getElementById('loginForm');
if(loginForm){
  loginForm.addEventListener('submit', async e =>{
    e.preventDefault();
    const fd = new FormData(loginForm);
    const body = {username: fd.get('username'), password: fd.get('password')};
    try{
      const json = await postJson('/api/login', body);
      if(json.success){
        showToast('Welcome back!');
        setTimeout(()=> location.href = '/home', 500);
      }
    }catch(err){
      showToast(err.message || 'Login failed');
    }
  })
}

// --- Signup page ---
const signupForm = document.getElementById('signupForm');
if(signupForm){
  signupForm.addEventListener('submit', async e =>{
    e.preventDefault();
    const fd = new FormData(signupForm);
    const body = {username: fd.get('username'), password: fd.get('password')};
    try{
      const json = await postJson('/api/signup', body);
      if(json.success){
        showToast('Account created — welcome!');
        setTimeout(()=> location.href = '/home', 500);
      }
    }catch(err){
      showToast(err.message || 'Signup failed');
    }
  })
}

// --- Home / app page ---
const homeApp = document.getElementById('homeApp');
if(homeApp){
  const entriesList = document.getElementById('entriesList');
  const greeting = document.getElementById('greeting');
  const logoutBtn = document.getElementById('logoutBtn');
  const newEntryBtn = document.getElementById('newEntryBtn');
  const entryModal = document.getElementById('entryModal');
  const closeModal = document.getElementById('closeModal');
  const cancelBtn = document.getElementById('cancelBtn');
  const entryForm = document.getElementById('entryForm');
  const entryId = document.getElementById('entryId');
  const entryTitle = document.getElementById('entryTitle');
  const entryContent = document.getElementById('entryContent');
  const modalTitle = document.getElementById('modalTitle');

  async function fetchMe(){
    const r = await fetch('/api/me');
    return r.json();
  }

  async function fetchEntries(){
    try{
      const r = await fetch('/api/entries');
      const j = await r.json();
      if(!j.success) throw new Error(j.error || 'Failed');
      renderEntries(j.entries || []);
    }catch(err){
      showToast('Could not load entries');
    }
  }

  function renderEntries(list){
    entriesList.innerHTML = '';
    if(list.length===0){
      entriesList.innerHTML = '<div class="card"><p class="muted">No entries yet — create your first one.</p></div>';
      return;
    }
    list.forEach(entry =>{
      const el = document.createElement('div'); el.className='card';
      const title = document.createElement('div'); title.className='entry-title'; title.textContent = entry.title || '(No title)';
      const meta = document.createElement('div'); meta.className='entry-meta'; meta.textContent = new Date(entry.created_at).toLocaleString();
      const content = document.createElement('div'); content.className='entry-content'; content.textContent = entry.content || '';
      const actions = document.createElement('div'); actions.className='card-actions';

      const editBtn = document.createElement('button'); editBtn.className='btn ghost'; editBtn.textContent='Edit';
      editBtn.addEventListener('click', ()=> openEdit(entry));
      const delBtn = document.createElement('button'); delBtn.className='btn ghost'; delBtn.textContent='Delete';
      delBtn.addEventListener('click', ()=> delEntry(entry.id));

      actions.appendChild(editBtn); actions.appendChild(delBtn);
      el.appendChild(title); el.appendChild(meta); el.appendChild(content); el.appendChild(actions);
      entriesList.appendChild(el);
    })
  }

  async function delEntry(id){
    if(!confirm('Delete this entry?')) return;
    try{
      const r = await fetch('/api/entries/' + id, {method:'DELETE'});
      const j = await r.json();
      if(!j.success) throw new Error(j.error || 'Delete failed');
      showToast('Deleted');
      fetchEntries();
    }catch(err){ showToast(err.message) }
  }

  function openModal(){ entryModal.setAttribute('aria-hidden','false'); }
  function closeModalFn(){ entryModal.setAttribute('aria-hidden','true'); entryForm.reset(); entryId.value=''; }

  function openNew(){ modalTitle.textContent='New Entry'; entryId.value=''; entryTitle.value=''; entryContent.value=''; openModal(); }
  function openEdit(entry){ modalTitle.textContent='Edit Entry'; entryId.value = entry.id; entryTitle.value = entry.title; entryContent.value = entry.content; openModal(); }

  entryForm.addEventListener('submit', async e =>{
    e.preventDefault();
    const id = entryId.value;
    const body = {title: entryTitle.value, content: entryContent.value};
    try{
      if(id){
        const r = await fetch('/api/entries/' + id, {method:'PUT', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
        const j = await r.json(); if(!j.success) throw new Error(j.error||'Save failed');
        showToast('Saved');
      } else {
        const r = await fetch('/api/entries', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
        const j = await r.json(); if(!j.success) throw new Error(j.error||'Save failed');
        showToast('Saved');
      }
      closeModalFn();
      fetchEntries();
    }catch(err){ showToast(err.message) }
  })

  newEntryBtn.addEventListener('click', openNew);
  closeModal.addEventListener('click', closeModalFn);
  cancelBtn.addEventListener('click', closeModalFn);

  logoutBtn.addEventListener('click', async ()=>{
    await postJson('/api/logout', {});
    location.href = '/';
  })

  // initial load
  (async ()=>{
    const me = await fetchMe();
    if(!me.logged_in) return location.href = '/';
    greeting.textContent = `Hi, ${me.username}`;
    fetchEntries();
  })();
}
