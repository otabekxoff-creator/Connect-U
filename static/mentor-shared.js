/* ================================================================
   ConnectU — Mentor Panel · Shared State & Utilities
   mentor-shared.js — barcha mentor fayllar shu faylni import qiladi
   ================================================================ */

/* ─── GLOBAL STATE ─── */
window.CU = window.CU || {};
CU.currentUser   = null;
CU.mentorData    = null;
CU.sessions      = [];
CU.pointsHistory = [];
CU.certificates  = [];
CU.videos        = [];
CU.notifs        = [];
CU.news          = [];

/* ─── API BASE ─── */
CU.API = {
  base: '',
  async get(path) {
    const r = await fetch(this.base + path, {credentials:'include'});
    return r.json();
  },
  async post(path, body) {
    const r = await fetch(this.base + path, {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify(body), credentials:'include'
    });
    return r.json();
  },
  async put(path, body) {
    const r = await fetch(this.base + path, {
      method:'PUT', headers:{'Content-Type':'application/json'},
      body: JSON.stringify(body), credentials:'include'
    });
    return r.json();
  },
  async del(path) {
    const r = await fetch(this.base + path, {method:'DELETE', credentials:'include'});
    return r.json();
  }
};

/* ─── AUTH ─── */
CU.init = async function(onSuccess) {
  try {
    const tg = window.Telegram?.WebApp;
    if(tg){tg.ready();tg.expand();}
    
    const d = await CU.API.get('/api/me');
    if(!d.success) { location.href='login.html'; return; }
    CU.currentUser = d.user;
    if(CU.currentUser.role !== 'mentor') { location.href='index.html'; return; }
    if(CU.currentUser.mentor_profile) CU.mentorData = CU.currentUser.mentor_profile;

    CU.applyTheme();

    await Promise.allSettled([
      CU.loadSessions(),
      CU.loadPoints(),
      CU.loadCertificates(),
      CU.loadVerificationStatus(),
    ]);

    if(onSuccess) onSuccess();

    const ls = document.getElementById('loadingScreen');
    const shell = document.getElementById('appShell');
    if(ls) ls.style.display = 'none';
    if(shell) shell.style.display = 'flex';

  } catch(e) {
    console.error('Init error:', e);
    location.href = 'login.html';
  }
};

CU.logout = async function() {
  try { await fetch('/api/logout',{method:'POST',credentials:'include'}); } catch(e){}
  location.href = 'login.html';
};

/* ─── DATA LOADERS ─── */
CU.loadSessions = async function() {
  try {
    const d = await CU.API.get('/api/sessions');
    if(d.success) CU.sessions = d.sessions || [];
  } catch(e) { console.error(e); }
};

CU.loadPoints = async function() {
  try {
    const d = await CU.API.get('/api/mentor/points');
    if(d.success) CU.pointsHistory = d.points || [];
  } catch(e) { console.error(e); }
};

CU.loadCertificates = async function() {
  try {
    const d = await CU.API.get('/api/mentor/certificates');
    if(d.success) CU.certificates = d.certificates || [];
  } catch(e) { console.error(e); }
};

CU.loadVerificationStatus = async function() {
  try {
    const d = await CU.API.get('/api/mentor/student-id-status');
    if(d.success) CU._verifyData = d;
    return d;
  } catch(e) { return null; }
};

CU.loadVideos = async function() {
  try {
    const d = await CU.API.get('/api/materials');
    if(d.success) CU.videos = d.materials || [];
  } catch(e) { CU.videos = CU._demoVideos(); }
};

/* ─── DEMO DATA ─── */
CU._demoVideos = function() {
  return [
    {id:'v1',title:'DTM matematika — kasr va nisbat',url:'https://youtu.be/dQw4w9WgXcQ',thumbnail:'https://img.youtube.com/vi/dQw4w9WgXcQ/hqdefault.jpg',access:'free',views:248,likes:34,description:'2024-2025 DTM dasturi bo\'yicha asosiy mavzular',created_at:new Date(Date.now()-86400000*2).toISOString()},
    {id:'v2',title:'TDYU kirish imtihoniga tayyorlash strategiyasi',url:'https://youtu.be/9bZkp7q19f0',thumbnail:'https://img.youtube.com/vi/9bZkp7q19f0/hqdefault.jpg',access:'premium',views:156,likes:22,description:'TDYU 2025-2026 yil uchun to\'liq tayyorgarlik rejasi',created_at:new Date(Date.now()-86400000*5).toISOString()},
    {id:'v3',title:'Ingliz tili: Grammar essentials B1→B2',url:'https://youtu.be/XqZsoesa55w',thumbnail:'https://img.youtube.com/vi/XqZsoesa55w/hqdefault.jpg',access:'free',views:312,likes:51,description:'B1 dan B2 darajasiga o\'tish uchun zarur grammar mavzular',created_at:new Date(Date.now()-86400000*8).toISOString()},
    {id:'v4',title:'IELTS Speaking — Band 7+ strategiya',url:'',thumbnail:'',access:'premium',views:89,likes:15,description:'IELTS Speaking bandini 7 yoki undan yuqori qilish usullari',created_at:new Date(Date.now()-86400000*12).toISOString()},
  ];
};

CU._demoNews = function() {
  return [
    {id:'n1',title:'📋 Yangi to\'lov tizimi ishga tushdi',content:'Endi sessiyangizdagi to\'lovlar 24 soat ichida balansga tushadi.',category:'update',priority:'high',created_at:new Date().toISOString()},
    {id:'n2',title:'📅 Mentor webinari: Dars o\'tish texnikasi',content:'Kelasi juma kuni mentor webinari bo\'lib o\'tadi.',category:'event',priority:'normal',link:'https://t.me/connectu_admin',created_at:new Date(Date.now()-86400000*2).toISOString()},
    {id:'n3',title:'⚠️ Profil to\'ldirilmagan mentorlar',content:'30% dan kam to\'ldirilgan profil 3 kun ichida archivga o\'tkaziladi.',category:'urgent',priority:'critical',created_at:new Date(Date.now()-86400000*3).toISOString()},
  ];
};

/* ─── UTILS ─── */
CU.fmt = function(n) {
  if(n===undefined||n===null) return '0';
  return Math.abs(n).toLocaleString('uz-UZ');
};

CU.fmtDate = function(str) {
  if(!str) return '—';
  const d = new Date(str), now = new Date(), diff = d - now;
  if(diff < 0) {
    const ago = Math.floor(-diff/86400000);
    if(ago === 0) return 'Bugun'; if(ago === 1) return 'Kecha'; return `${ago} kun oldin`;
  }
  const days = Math.floor(diff/86400000);
  const t = `${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`;
  if(days===0) return `Bugun ${t}`; if(days===1) return `Ertaga ${t}`;
  return `${d.getDate()}.${d.getMonth()+1} ${t}`;
};

CU.fmtDateShort = function(str) {
  if(!str) return '—';
  const d = new Date(str);
  return `${d.getDate()}.${String(d.getMonth()+1).padStart(2,'0')}.${d.getFullYear()}`;
};

CU.timeAgo = function(str) {
  if(!str) return '';
  const sec = Math.floor((Date.now() - new Date(str)) / 1000);
  if(sec < 60) return 'Hozirgina';
  if(sec < 3600) return Math.floor(sec/60) + ' daqiqa oldin';
  if(sec < 86400) return Math.floor(sec/3600) + ' soat oldin';
  if(sec < 7*86400) return Math.floor(sec/86400) + ' kun oldin';
  return new Date(str).toLocaleDateString('uz-UZ');
};

CU.strColor = function(str) {
  let h = 0;
  for(let i=0;i<(str||'').length;i++) h = str.charCodeAt(i)+((h<<5)-h);
  return ['#1e3a6e','#2d1b69','#1a3a2a','#3a1a2a','#6e1e3a','#1e4040','#2a1a40'][Math.abs(h)%7];
};

CU.escHtml = function(s) {
  if(!s) return '';
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
};

CU.ytThumb = function(url) {
  const m = (url||'').match(/(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\s]+)/);
  return m ? `https://img.youtube.com/vi/${m[1]}/hqdefault.jpg` : '';
};

/* ─── TOAST ─── */
let _toastTimer;
CU.toast = function(msg, type='ok') {
  clearTimeout(_toastTimer);
  let el = document.getElementById('_cuToast');
  if(!el) {
    el = document.createElement('div');
    el.id = '_cuToast';
    el.style.cssText = 'position:fixed;bottom:86px;left:50%;transform:translateX(-50%);background:#1A2A4A;color:#fff;padding:11px 22px;border-radius:20px;font-size:13px;font-weight:600;z-index:9999;box-shadow:0 4px 24px rgba(0,0,0,.6);white-space:nowrap;transition:opacity .3s;pointer-events:none;max-width:90vw;text-align:center';
    document.body.appendChild(el);
  }
  el.textContent = msg;
  el.style.borderLeft = type==='err' ? '3px solid #FF4D6A' : '3px solid #00BFA6';
  el.style.opacity = '1';
  _toastTimer = setTimeout(() => el.style.opacity='0', 2800);
};

/* ─── THEME ─── */
CU.applyTheme = function() {
  if(localStorage.getItem('cu_theme') === 'light') {
    document.body.classList.add('light-theme');
    const btn = document.getElementById('themeToggleBtn');
    if(btn) { btn.querySelector('.theme-icon').textContent = '☀️'; btn.querySelector('.theme-lbl').textContent = 'Qora rejim'; }
  }
};
CU.toggleTheme = function() {
  const isLight = document.body.classList.toggle('light-theme');
  localStorage.setItem('cu_theme', isLight ? 'light' : 'dark');
  const btn = document.getElementById('themeToggleBtn');
  if(btn) { btn.querySelector('.theme-icon').textContent = isLight ? '☀️' : '🌙'; btn.querySelector('.theme-lbl').textContent = isLight ? 'Qora rejim' : 'Oq rejim'; }
};

/* ─── MODAL (bottom sheet) ─── */
CU.openModal = function(id) {
  const el = document.getElementById(id);
  if(el) { el.classList.add('open'); document.body.style.overflow = 'hidden'; }
};
CU.closeModal = function(id) {
  const el = document.getElementById(id);
  if(el) { el.classList.remove('open'); document.body.style.overflow = ''; }
};

/* ─── SESSION HELPERS ─── */
CU.sessionBadge = function(status) {
  const m = {pending:'<span class="badge b-gold">Kutilmoqda</span>',confirmed:'<span class="badge b-teal">Tasdiqlangan</span>',completed:'<span class="badge b-green">Tugallandi</span>',cancelled:'<span class="badge b-red">Bekor</span>'};
  return m[status] || '';
};
CU.sessionPts = function(type) {
  return type === 'individual' ? 8000 : type === 'group' ? 2000 : 0;
};
CU.sessionTypeLabel = function(type) {
  return type === 'individual' ? 'Individual' : type === 'group' ? 'Guruh' : (type||'').toUpperCase();
};

CU.confirmSession = async function(id, onDone) {
  try {
    const d = await CU.API.post(`/api/sessions/${id}/confirm`, {});
    if(d.success) {
      const s = CU.sessions.find(x=>x.id===id);
      if(s) s.status = 'confirmed';
      CU.toast('Sessiya tasdiqlandi ✓');
      if(onDone) onDone();
    } else CU.toast(d.error||'Xatolik','err');
  } catch(e) { CU.toast('Server xatosi','err'); }
};

CU.rejectSession = async function(id, onDone) {
  try {
    const d = await CU.API.post(`/api/sessions/${id}/reject`, {});
    if(d.success) {
      const s = CU.sessions.find(x=>x.id===id);
      if(s) s.status = 'cancelled';
      CU.toast('Rad etildi');
      if(onDone) onDone();
    } else CU.toast(d.error||'Xatolik','err');
  } catch(e) { CU.toast('Server xatosi','err'); }
};

/* ─── NAVIGATION ─── */
CU.PAGES = {
  'home':     '/mentor-dashboard.html',
  'sessions': '/mentor-sessions.html',
  'videos':   '/mentor-videos.html',
  'earnings': '/mentor-earnings.html',
  'profile':  '/mentor-profile.html',
};

CU.navTo = function(page) {
  const url = CU.PAGES[page];
  if(url) location.href = url;
};

/* ─── ACTIVE NAV HIGHLIGHT ─── */
CU.highlightNav = function(current) {
  document.querySelectorAll('.ni').forEach(n => {
    const page = n.dataset.page;
    n.classList.toggle('active', page === current);
  });
};
