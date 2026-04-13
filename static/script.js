// ══════════════════════════════════════════════════════════════════════════════
//  MentalTalk — Client-Side JavaScript
//  Injected via Gradio launch(head=...) so all functions are at global scope.
// ══════════════════════════════════════════════════════════════════════════════

// ── STATE ────────────────────────────────────────────────────────────────────
var currentUser = 'Friend';
var currentMood = 3;
var sessionCount = 0;
var moodHistory = [];   // [{score, label, color, date}]
var chatHistory = [];   // [{user, bot, mood_label, color, date}]
var isWaiting = false;
var isGuest = true; // true = no DB persistence

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

//  LOGIN / SIGNUP — Server-validated via Gradio bridge

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
    if (loading) btns[i].classList.add('loading');
    else btns[i].classList.remove('loading');
  }
}

function doLogin() {
  var name = (document.getElementById('li-name').value || '').trim();
  var pass = document.getElementById('li-pass').value || '';
  document.getElementById('auth-error').style.display = 'none';

  if (!name || !pass) {
    showAuthError('Please enter both username and password');
    return;
  }

  setAuthLoading(true);
  sendAuthToGradio({ action: 'login', username: name, password: pass });
}

function doSignup() {
  var name = (document.getElementById('su-name').value || '').trim();
  var pass = document.getElementById('su-pass').value || '';
  document.getElementById('auth-error').style.display = 'none';

  if (!name || !pass) {
    showAuthError('Please enter both username and password');
    return;
  }
  if (name.length < 3) {
    showAuthError('Username must be at least 3 characters');
    return;
  }
  if (pass.length < 4) {
    showAuthError('Password must be at least 4 characters');
    return;
  }

  setAuthLoading(true);
  sendAuthToGradio({ action: 'signup', username: name, password: pass });
}

/** Called by Gradio bridge when Python returns auth result */
function receiveAuth(jsonStr) {
  setAuthLoading(false);

  var resp;
  try { resp = JSON.parse(jsonStr); } catch (e) { showAuthError('Unexpected error'); return; }

  if (!resp.ok) {
    showAuthError(resp.error || 'Authentication failed');
    return;
  }

  // Auth successful — apply user
  currentUser = resp.username || 'Friend';
  isGuest = false;

  // Restore stats
  if (resp.stats) {
    sessionCount = resp.stats.session_count || 0;
    document.getElementById('sess-count').textContent = sessionCount;
    var streak = resp.stats.streak || 0;
    document.getElementById('streak-txt').textContent =
      streak >= 2 ? streak + '-Day Streak!' : 'Start your streak!';
  }

  // Restore mood history (from DB)
  if (resp.moods && resp.moods.length > 0) {
    moodHistory = [];
    for (var i = 0; i < resp.moods.length; i++) {
      var m = resp.moods[i];
      moodHistory.push({
        score: m.score,
        label: m.label,
        color: m.color,
        date: m.day_short || ''
      });
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

function applyUser() {
  document.getElementById('modal-bg').classList.add('hidden');
  document.getElementById('u-name').textContent = currentUser;
  document.getElementById('u-initial').textContent = currentUser[0].toUpperCase();
  document.getElementById('greet-name').textContent = currentUser;
  document.getElementById('topbar-title').innerHTML =
    'Welcome back, <span style="color:var(--accent2)">' + currentUser + '</span> \ud83d\udc4b';
  // Push username to Gradio backend state
  pushUsernameToGradio(currentUser);
}


//  CRISIS TOGGLE
function toggleCrisis() {
  var cb = document.getElementById('crisis-bar');
  cb.style.display = cb.style.display === 'none' ? 'block' : 'none';
}

//  MOOD

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

  // Record locally
  var d = new Date();
  moodHistory.push({
    score: score, label: MOOD_LABELS[score], color: meta[1],
    date: DAY_SHORT[d.getDay()]
  });
  renderChart();
  updateStats();

  // Push to Gradio Python state (DB persistence for registered users)
  pushMoodToGradio(score, MOOD_LABELS[score], meta[1], DAY_SHORT[d.getDay()]);
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

//  CHAT
function quickSend(btn) {
  var text = btn.textContent.replace(/^[^\s]+\s/, '');
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
  sendToGradio(text);
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

// Called by Gradio after Python responds
function receiveReply(botText, historyHtml) {
  hideTyping();
  isWaiting = false;
  appendMsg('ai', botText);
  sessionCount++;
  document.getElementById('sess-count').textContent = sessionCount;
  if (historyHtml) document.getElementById('hist-list').innerHTML = historyHtml;
}

//  GRADIO BRIDGE — communicates with Python backend via hidden textboxes

/** Find the inner <textarea> or <input> inside a Gradio component by its elem_id */
function findGradioInput(elemId) {
  var container = document.getElementById(elemId);
  if (!container) return null;
  return container.querySelector('textarea') || container.querySelector('input');
}

/** Set a hidden Gradio textbox value and dispatch an input event */
function setGradioValue(elemId, value) {
  var el = findGradioInput(elemId);
  if (!el) { console.warn('Bridge element not found:', elemId); return; }
  var nativeSetter = Object.getOwnPropertyDescriptor(
    window.HTMLTextAreaElement.prototype, 'value'
  ) || Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value');
  if (nativeSetter && nativeSetter.set) {
    nativeSetter.set.call(el, value);
  } else {
    el.value = value;
  }
  el.dispatchEvent(new Event('input', { bubbles: true }));
}

/** Trigger a .submit() by dispatching Enter keydown */
function triggerGradioSubmit(elemId) {
  var el = findGradioInput(elemId);
  if (!el) return;
  setTimeout(function () {
    el.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', keyCode: 13, bubbles: true }));
  }, 50);
}

/** Send a chat message to Python */
function sendToGradio(text) {
  var el = findGradioInput('gradio-user-input');
  if (!el) { console.warn('Chat bridge not found'); receiveReply('Bridge error — please reload.', ''); return; }

  var setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value');
  if (setter && setter.set) setter.set.call(el, text);
  else el.value = text;
  el.dispatchEvent(new Event('input', { bubbles: true }));
  triggerGradioSubmit('gradio-user-input');
}

/** Send auth request to Python */
function sendAuthToGradio(data) {
  var el = findGradioInput('gradio-auth-input');
  if (!el) { showAuthError('Auth bridge not ready — please reload'); setAuthLoading(false); return; }

  var payload = JSON.stringify(data);
  var setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value');
  if (setter && setter.set) setter.set.call(el, payload);
  else el.value = payload;
  el.dispatchEvent(new Event('input', { bubbles: true }));
  triggerGradioSubmit('gradio-auth-input');
}

/** Push mood data to Python for persistence */
function pushMoodToGradio(score, label, color, dayShort) {
  var el = findGradioInput('gradio-mood-input');
  if (!el) return;
  var payload = JSON.stringify({ score: score, label: label, color: color, date: dayShort });
  var setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value');
  if (setter && setter.set) setter.set.call(el, payload);
  else el.value = payload;
  el.dispatchEvent(new Event('input', { bubbles: true }));
  triggerGradioSubmit('gradio-mood-input');
}

/** Push the username to Python so it can track per-user */
function pushUsernameToGradio(name) {
  setGradioValue('gradio-username-input', name);
}
