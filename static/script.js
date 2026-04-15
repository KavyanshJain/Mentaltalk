// ══════════════════════════════════════════════════════════════════════════════
//  MentalTalk — Client-Side JavaScript  (Gradio 6.x compatible)
// ══════════════════════════════════════════════════════════════════════════════

// ── STATE ────────────────────────────────────────────────────────────────────
var currentUser = 'Friend';
var currentMood = 3;
var sessionCount = 0;
var moodHistory = [];
var chatHistory = [];
var isWaiting = false;
var isGuest = true;

// ── BOOT ─────────────────────────────────────────────────────────────────────
function mtInit() {
  var mcDate = document.getElementById('mc-date');
  if (!mcDate) { setTimeout(mtInit, 200); return; }
  var d = new Date();
  mcDate.textContent = d.toLocaleDateString('en-IN', { weekday: 'short', month: 'short', day: 'numeric' });
}
document.addEventListener('DOMContentLoaded', mtInit);
setTimeout(mtInit, 500);
setTimeout(mtInit, 1500);

// ── GRADIO 6.x BRIDGE ────────────────────────────────────────────────────────
// Gradio 6.x uses Svelte internally. The reliable dispatch sequence is:
// native setter → input event on inner element → change event on inner element
// → input event on wrapper container → Enter keydown after 50ms delay.

function _gradioSubmit(elemId, value) {
  var container = document.getElementById(elemId);
  if (!container) {
    console.error('[Bridge] Container not found:', elemId);
    return false;
  }

  var inner = container.querySelector('textarea') || container.querySelector('input');
  if (!inner) {
    console.error('[Bridge] Inner input not found in:', elemId);
    return false;
  }

  // Set value via native setter to bypass Svelte's reactive state
  var proto = (inner.tagName === 'TEXTAREA')
    ? window.HTMLTextAreaElement.prototype
    : window.HTMLInputElement.prototype;
  var setter = Object.getOwnPropertyDescriptor(proto, 'value');
  if (setter && setter.set) setter.set.call(inner, value);
  else inner.value = value;

  // Fire events in order Gradio 6.x expects
  inner.dispatchEvent(new Event('input', { bubbles: true }));
  inner.dispatchEvent(new Event('change', { bubbles: true }));
  container.dispatchEvent(new Event('input', { bubbles: true }));

  // Enter keydown triggers .submit() binding after state settles
  setTimeout(function () {
    inner.dispatchEvent(new KeyboardEvent('keydown', {
      key: 'Enter', code: 'Enter', keyCode: 13, which: 13,
      bubbles: true, cancelable: true, composed: true
    }));
    inner.dispatchEvent(new KeyboardEvent('keyup', {
      key: 'Enter', code: 'Enter', keyCode: 13, which: 13,
      bubbles: true, cancelable: true
    }));
  }, 50);

  return true;
}

// ── AUTH ──────────────────────────────────────────────────────────────────────
function switchTab(t) {
  document.getElementById('login-form').style.display = t === 'login' ? 'block' : 'none';
  document.getElementById('signup-form').style.display = t === 'signup' ? 'block' : 'none';
  document.getElementById('auth-error').style.display = 'none';
  var tabs = document.querySelectorAll('.tab-btn');
  for (var i = 0; i < tabs.length; i++) {
    tabs[i].classList.toggle('active', (i === 0 && t === 'login') || (i === 1 && t === 'signup'));
  }
}

function showAuthError(msg) {
  var el = document.getElementById('auth-error');
  el.textContent = msg;
  el.style.display = 'block';
}

function setAuthLoading(loading) {
  var btns = document.querySelectorAll('#login-btn, #signup-btn');
  for (var i = 0; i < btns.length; i++) {
    btns[i].disabled = loading;
    btns[i].classList.toggle('loading', loading);
  }
}

function doLogin() {
  var name = (document.getElementById('li-name').value || '').trim();
  var pass = document.getElementById('li-pass').value || '';
  document.getElementById('auth-error').style.display = 'none';
  if (!name || !pass) { showAuthError('Please enter both username and password'); return; }
  setAuthLoading(true);
  var ok = _gradioSubmit('gradio-auth-input', JSON.stringify({ action: 'login', username: name, password: pass }));
  if (!ok) { showAuthError('Auth bridge not ready — please reload'); setAuthLoading(false); }
}

function doSignup() {
  var name = (document.getElementById('su-name').value || '').trim();
  var pass = document.getElementById('su-pass').value || '';
  document.getElementById('auth-error').style.display = 'none';
  if (!name || !pass) { showAuthError('Please enter both username and password'); return; }
  if (name.length < 3) { showAuthError('Username must be at least 3 characters'); return; }
  if (pass.length < 4) { showAuthError('Password must be at least 4 characters'); return; }
  setAuthLoading(true);
  var ok = _gradioSubmit('gradio-auth-input', JSON.stringify({ action: 'signup', username: name, password: pass }));
  if (!ok) { showAuthError('Auth bridge not ready — please reload'); setAuthLoading(false); }
}

function receiveAuth(jsonStr) {
  setAuthLoading(false);
  var resp;
  try { resp = JSON.parse(jsonStr); } catch (e) { showAuthError('Unexpected error'); return; }
  if (!resp.ok) { showAuthError(resp.error || 'Authentication failed'); return; }

  currentUser = resp.username || 'Friend';
  isGuest = false;

  if (resp.stats) {
    sessionCount = resp.stats.session_count || 0;
    document.getElementById('sess-count').textContent = sessionCount;
    var streak = resp.stats.streak || 0;
    document.getElementById('streak-txt').textContent =
      streak >= 2 ? streak + '-Day Streak!' : 'Start your streak!';
  }

  if (resp.moods && resp.moods.length > 0) {
    moodHistory = [];
    for (var i = 0; i < resp.moods.length; i++) {
      var m = resp.moods[i];
      moodHistory.push({ score: m.score, label: m.label, color: m.color, date: m.day_short || '' });
    }
    renderChart();
    updateStats();
  }

  applyUser();
}

function doGuest() {
  currentUser = 'Friend';
  isGuest = true;
  applyUser();
}

function doLogout() {
  currentUser = 'Friend';
  isGuest = true;
  sessionCount = 0;
  moodHistory = [];
  chatHistory = [];
  isWaiting = false;
  if (typingEl) { typingEl.remove(); typingEl = null; }

  document.getElementById('msgs').innerHTML = '';
  document.getElementById('msgs').classList.remove('open');
  document.getElementById('welcome').classList.remove('hidden');
  document.getElementById('hist-list').innerHTML =
    '<p style="color:var(--muted);font-size:12px;padding:8px 16px">No conversations yet</p>';
  document.getElementById('sess-count').textContent = '0';
  document.getElementById('avg-mood').textContent = '\u2014';
  document.getElementById('streak-txt').textContent = 'Start your streak!';
  document.getElementById('chart-body').innerHTML =
    '<p style="color:var(--muted);font-size:12px;text-align:center;padding:16px 0">Log moods to see your pattern</p>';

  document.getElementById('modal-bg').classList.remove('hidden');
  document.getElementById('li-name').value = '';
  document.getElementById('li-pass').value = '';
  document.getElementById('auth-error').style.display = 'none';
  switchTab('login');
}

function applyUser() {
  document.getElementById('modal-bg').classList.add('hidden');
  document.getElementById('u-name').textContent = currentUser;
  document.getElementById('u-initial').textContent = currentUser[0].toUpperCase();
  document.getElementById('greet-name').textContent = currentUser;
  document.getElementById('topbar-title').innerHTML =
    'Welcome back, <span style="color:var(--accent2)">' + currentUser + '</span> \ud83d\udc4b';

  // Push username to Gradio state (value-only, no submit needed)
  var container = document.getElementById('gradio-username-input');
  if (container) {
    var inner = container.querySelector('textarea') || container.querySelector('input');
    if (inner) {
      var proto = inner.tagName === 'TEXTAREA' ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
      var setter = Object.getOwnPropertyDescriptor(proto, 'value');
      if (setter && setter.set) setter.set.call(inner, currentUser);
      else inner.value = currentUser;
      inner.dispatchEvent(new Event('input', { bubbles: true }));
    }
  }
}

// ── CRISIS ────────────────────────────────────────────────────────────────────
function toggleCrisis() {
  var cb = document.getElementById('crisis-bar');
  cb.style.display = cb.style.display === 'none' ? 'block' : 'none';
}

// ── MOOD ──────────────────────────────────────────────────────────────────────
var MOOD_META = {
  5: ['Feeling great today! \ud83c\udf1f', '#63b396'],
  4: ['Having a good day \ud83d\ude0a', '#a8d5c2'],
  3: ['Feeling okay today', '#e8c4a0'],
  2: ['A bit low today \ud83d\udc99', '#f0a0a0'],
  1: ['Having a hard time \ud83d\udc9c', '#e57373'],
};
var MOOD_LABELS = { 5: '\ud83d\ude04 Great', 4: '\ud83d\ude0a Good', 3: '\ud83d\ude10 Okay', 2: '\ud83d\ude14 Low', 1: '\ud83d\ude22 Hard' };
var DAY_SHORT = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

function pickMood(score, btn) {
  currentMood = score;
  var btns = document.querySelectorAll('.mbtn');
  for (var i = 0; i < btns.length; i++) btns[i].classList.remove('sel');
  btn.classList.add('sel');
  var meta = MOOD_META[score];
  document.getElementById('mood-score').textContent = score;
  document.getElementById('mood-lbl').textContent = meta[0];

  var d = new Date();
  moodHistory.push({ score: score, label: MOOD_LABELS[score], color: meta[1], date: DAY_SHORT[d.getDay()] });
  renderChart();
  updateStats();

  _gradioSubmit('gradio-mood-input', JSON.stringify({
    score: score, label: MOOD_LABELS[score], color: meta[1], date: DAY_SHORT[d.getDay()]
  }));
}

function renderChart() {
  var recent = moodHistory.slice(-7);
  if (!recent.length) return;
  var bars = '';
  for (var i = 0; i < recent.length; i++) {
    var e = recent[i];
    var h = Math.max(8, Math.round((e.score / 5) * 60));
    bars += '<div class="cb-wrap">' +
      '<div class="cb-bar" style="height:' + h + 'px;background:linear-gradient(to top,' + e.color + ',' + e.color + '88)" title="' + e.label + '"></div>' +
      '<span class="cb-day">' + e.date + '</span></div>';
  }
  var sum = 0;
  for (var j = 0; j < recent.length; j++) sum += recent[j].score;
  var avg = (sum / recent.length).toFixed(1);
  document.getElementById('chart-body').innerHTML =
    '<div class="chart-inner"><div class="cb-row">' + bars + '</div>' +
    '<div class="cb-avg">7-day avg: <b style="color:#63b396">' + avg + '/5</b></div></div>';
  document.getElementById('avg-mood').textContent = avg;
}

function updateStats() {
  document.getElementById('sess-count').textContent = sessionCount;
  var n = moodHistory.length;
  document.getElementById('streak-txt').textContent = n >= 2 ? n + '-Day Streak!' : 'Start your streak!';
}

// ── CHAT ──────────────────────────────────────────────────────────────────────
function quickSend(btn) {
  var raw = btn.textContent || btn.innerText || '';
  // Strip leading emoji + space robustly
  var text = raw.replace(/^[\u{1F300}-\u{1FFFF}\u{2600}-\u{26FF}\u{2700}-\u{27BF} ]+/u, '').trim();
  if (!text) text = raw.trim();
  document.getElementById('inp').value = text;
  triggerSend();
}

function autoGrow(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 100) + 'px';
}

function escapeHtml(text) {
  var map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
  return text.replace(/[&<>"']/g, function (c) { return map[c]; });
}

function triggerSend() {
  if (isWaiting) return;
  var inp = document.getElementById('inp');
  var text = inp.value.trim();
  if (!text) return;
  inp.value = '';
  inp.style.height = 'auto';
  showChat();
  appendMsg('user', escapeHtml(text));
  showTyping();
  isWaiting = true;

  var ok = _gradioSubmit('gradio-user-input', text);
  if (!ok) {
    hideTyping();
    isWaiting = false;
    appendMsg('ai', 'Connection error — could not reach backend. Please reload the page.');
  }
}

function showChat() {
  document.getElementById('welcome').classList.add('hidden');
  document.getElementById('msgs').classList.add('open');
}

function appendMsg(role, html) {
  var msgs = document.getElementById('msgs');
  var div = document.createElement('div');
  div.className = 'msg ' + role;
  div.innerHTML = '<div class="avatar ' + role + '">' + (role === 'ai' ? '\ud83e\udde0' : '\ud83d\udc64') + '</div>' +
    '<div class="bubble">' + html + '</div>';
  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
}

var typingEl = null;
function showTyping() {
  var msgs = document.getElementById('msgs');
  typingEl = document.createElement('div');
  typingEl.className = 'msg ai';
  typingEl.innerHTML = '<div class="avatar ai">\ud83e\udde0</div>' +
    '<div class="bubble"><div class="typing-dots">' +
    '<div class="td"></div><div class="td"></div><div class="td"></div>' +
    '</div></div>';
  msgs.appendChild(typingEl);
  msgs.scrollTop = msgs.scrollHeight;
}

function hideTyping() {
  if (typingEl) { typingEl.remove(); typingEl = null; }
}

function receiveReply(botText, historyHtml) {
  hideTyping();
  isWaiting = false;
  appendMsg('ai', botText);
  sessionCount++;
  document.getElementById('sess-count').textContent = sessionCount;
  if (historyHtml) document.getElementById('hist-list').innerHTML = historyHtml;
}