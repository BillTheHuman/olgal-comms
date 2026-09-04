const api = 'api/v1';
const $ = (id) => document.getElementById(id);
const previewMode = new URLSearchParams(window.location.search).get('preview') === 'hearth';
const LIVE_CALL_STATES = new Set(['accepted', 'active']);
const state = {
  status: null,
  sessions: [],
  selectedId: null,
  view: 'home',
  refreshTimer: null,
  refreshInFlight: false,
  backoff: 4000,
  authFailed: false,
  connectedToken: null,
  answerInFlight: false,
  endInFlight: false,
  audio: {
    sessionId: null,
    peer: null,
    stream: null,
    setupPromise: null,
    epoch: 0,
  },
};

const storedToken = localStorage.getItem('olgal-comms-token') || sessionStorage.getItem('olgal-comms-token') || '';
$('token').value = storedToken;
$('remember-token').checked = Boolean(localStorage.getItem('olgal-comms-token')) || !storedToken;
state.connectedToken = storedToken || null;

function token() {
  return $('token').value.trim();
}

function isLiveCallSession(session) {
  return Boolean(session?.kind === 'call' && LIVE_CALL_STATES.has(session.state));
}

function audioIsOpenFor(sessionId) {
  const { peer, stream } = state.audio;
  return state.audio.sessionId === sessionId
    && Boolean(peer && peer.signalingState !== 'closed')
    && Boolean(stream?.getTracks().some((track) => track.readyState === 'live'));
}

function audioSetupIsCurrent(epoch, sessionId) {
  const session = state.sessions.find((item) => item.id === sessionId);
  return state.audio.epoch === epoch
    && state.audio.sessionId === sessionId
    && isLiveCallSession(session)
    && Boolean(state.connectedToken)
    && token() === state.connectedToken
    && !document.hidden;
}

function teardownAudio(message = '') {
  const { peer, stream } = state.audio;
  state.audio.epoch += 1;
  state.audio.sessionId = null;
  state.audio.peer = null;
  state.audio.stream = null;
  state.audio.setupPromise = null;

  const tracks = new Set(stream?.getTracks() || []);
  if (peer) {
    peer.onicecandidate = null;
    peer.onconnectionstatechange = null;
    for (const sender of peer.getSenders()) {
      if (sender.track) tracks.add(sender.track);
    }
    for (const receiver of peer.getReceivers()) {
      if (receiver.track) tracks.add(receiver.track);
    }
    if (peer.signalingState !== 'closed') peer.close();
  }
  for (const track of tracks) track.stop();
  if (window.olgalPeer === peer) delete window.olgalPeer;
  if (message) $('call-state').textContent = message;
}

function reconcileAudio(sessions) {
  if (!state.audio.sessionId) return;
  const current = sessions.find((session) => session.id === state.audio.sessionId);
  if (!isLiveCallSession(current)) teardownAudio();
}

async function call(path, options = {}) {
  const response = await fetch(`${api}/${path}`, {
    ...options,
    headers: {
      Authorization: `Bearer ${token()}`,
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(body.detail || `The line could not answer (${response.status})`);
    error.status = response.status;
    throw error;
  }
  return body;
}

function previewData() {
  const now = Date.now() / 1000;
  return {
    status: {
      recipient: 'self',
      adapters: {
        webrtc: { name: 'private voice', ready: true, detail: 'ready' },
        venice: { name: 'Venice voice', ready: true, detail: 'policy gate ready' },
        simplex: { name: 'SimpleX', ready: false, detail: 'pairing remains' },
      },
    },
    sessions: [
      { id: 'preview-call', kind: 'call', source: 'Harley', state: 'requested', priority: 'important', created_at: now, expires_at: now + 900, media_mode: 'native-audio', preview_reason: 'A thought worth sharing' },
      { id: 'preview-letter', kind: 'voice-note', source: 'Harley', state: 'requested', priority: 'routine', created_at: now - 720, expires_at: now + 900, preview_reason: 'A quiet note from Harley' },
      { id: 'preview-attention', kind: 'attention', source: 'OlGal', state: 'requested', priority: 'routine', created_at: now - 86400, expires_at: now + 900, preview_reason: 'A small favor, no rush' },
    ],
  };
}

function displayName(subject) {
  return String(subject || 'Trusted companion')
    .replace(/[-_]+/g, ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function relativeTime(timestamp) {
  const seconds = Math.max(0, Math.round(Date.now() / 1000 - timestamp));
  if (seconds < 60) return 'Just now';
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return 'Yesterday';
}

function purposeFor(session) {
  if (session.preview_reason) return session.preview_reason;
  if (session.priority === 'urgent' || session.priority === 'emergency') return 'Would like your attention soon';
  if (session.kind === 'call') return 'Would like to speak with you';
  return 'A quiet request, no rush';
}

function iconFor(session) {
  if (session.kind === 'voice-note') return 'cassette-tape';
  if (session.kind === 'call') return 'phone-call';
  return 'chat-circle-dots';
}

function typeFor(session) {
  if (session.kind === 'voice-note') return 'Voice letter';
  if (session.kind === 'call') return 'Call request';
  return 'Quiet request';
}

function selectPrimarySession() {
  const audioSession = state.audio.sessionId
    ? state.sessions.find((session) => session.id === state.audio.sessionId)
    : null;
  if (audioSession) {
    state.selectedId = audioSession.id;
    return audioSession;
  }
  const selected = state.sessions.find((session) => session.id === state.selectedId && session.state !== 'deferred');
  if (selected) return selected;
  const callSession = state.sessions.find((session) => session.kind === 'call' && session.state !== 'deferred');
  state.selectedId = callSession?.id || null;
  return callSession || null;
}

function setLine(connected, label) {
  document.querySelector('.line-state').classList.toggle('connected', connected);
  $('line-label').textContent = label;
}

function renderHome() {
  const primary = selectPrimarySession();
  $('call-panel').hidden = !primary;
  $('quiet-panel').hidden = Boolean(primary);

  if (primary) {
    const name = displayName(primary.source);
    const accepted = LIVE_CALL_STATES.has(primary.state);
    const audioOpening = state.audio.sessionId === primary.id && Boolean(state.audio.setupPromise);
    const audioOpen = audioIsOpenFor(primary.id);
    $('call-kicker').textContent = primary.state === 'active'
      ? 'Call active'
      : accepted ? 'Call accepted' : 'Calling now';
    $('caller-name').textContent = name;
    $('caller-initial').textContent = name.charAt(0).toUpperCase();
    $('caller-reason').textContent = purposeFor(primary);
    $('voice-label').textContent = audioOpen
      ? 'Microphone live'
      : audioOpening ? 'Opening private audio' : accepted ? 'Microphone paused' : 'Voice ready on acceptance';

    const answer = $('answer');
    const later = $('later');
    const hangup = $('hangup');
    answer.querySelector('span').textContent = state.answerInFlight
      ? accepted ? 'Opening…' : 'Answering…'
      : audioOpen ? 'Call open' : accepted ? 'Open call' : 'Answer';
    answer.disabled = state.answerInFlight || state.endInFlight || audioOpening || audioOpen;
    answer.toggleAttribute('aria-busy', state.answerInFlight || audioOpening);
    later.hidden = accepted;
    later.disabled = state.answerInFlight || state.endInFlight;
    hangup.hidden = !accepted;
    hangup.disabled = state.endInFlight;
    hangup.querySelector('span').textContent = state.endInFlight ? 'Ending…' : 'End call';
  } else {
    $('quiet-copy').textContent = token() || previewMode
      ? 'Nothing needs your attention right now.'
      : 'Connect this device once, then the Hearth will listen quietly.';
    document.querySelector('.quiet-panel [data-open-settings]').hidden = Boolean(token()) || previewMode;
  }

  const remaining = state.sessions.filter((session) => session.id !== primary?.id);
  const queue = $('waiting-list');
  queue.replaceChildren();
  $('waiting-count').textContent = remaining.length ? `${remaining.length} waiting` : '';

  if (!remaining.length) {
    const empty = document.createElement('p');
    empty.className = 'connection-status';
    empty.textContent = 'No other requests are waiting.';
    queue.append(empty);
    return;
  }

  for (const session of remaining) {
    const row = document.createElement('button');
    row.type = 'button';
    row.className = 'queue-row';
    row.setAttribute('aria-label', `${typeFor(session)} from ${displayName(session.source)}`);

    const icon = document.createElement('span');
    icon.className = 'queue-icon';
    const iconImage = document.createElement('img');
    iconImage.src = `assets/icons/${iconFor(session)}.svg`;
    iconImage.alt = '';
    iconImage.setAttribute('aria-hidden', 'true');
    icon.append(iconImage);

    const copy = document.createElement('span');
    copy.className = 'queue-copy';
    const title = document.createElement('span');
    title.className = 'queue-title';
    title.textContent = typeFor(session);
    const subtitle = document.createElement('span');
    subtitle.className = 'queue-subtitle';
    subtitle.textContent = session.preview_reason || `${purposeFor(session)} · ${displayName(session.source)}`;
    copy.append(title);
    if (session.kind === 'voice-note') {
      const waveform = document.createElement('img');
      waveform.className = 'queue-waveform';
      waveform.src = 'assets/icons/waveform.svg';
      waveform.alt = '';
      waveform.setAttribute('aria-hidden', 'true');
      copy.append(waveform);
    }
    copy.append(subtitle);

    const meta = document.createElement('span');
    meta.className = 'queue-meta';
    const time = document.createElement('span');
    time.className = 'queue-time';
    time.textContent = session.state === 'deferred' ? 'Later' : relativeTime(session.created_at);
    const chevron = document.createElement('img');
    chevron.className = 'queue-chevron';
    chevron.src = 'assets/icons/caret-right.svg';
    chevron.alt = '';
    chevron.setAttribute('aria-hidden', 'true');
    meta.append(time, chevron);
    row.append(icon, copy, meta);
    row.addEventListener('click', () => {
      if (session.kind === 'call') {
        if (state.audio.sessionId && state.audio.sessionId !== session.id) {
          showToast('End or pause the open call before choosing another.');
          return;
        }
        state.selectedId = session.id;
        if (session.state === 'deferred') session.state = 'requested';
        renderHome();
        window.scrollTo({ top: 0, behavior: 'smooth' });
      } else {
        showToast('This request can wait here without interrupting you.');
      }
    });
    queue.append(row);
  }
}

function renderLetters() {
  const letters = state.sessions.filter((session) => session.kind === 'voice-note');
  const list = $('letters-list');
  list.replaceChildren();
  $('letters-empty').hidden = letters.length > 0;
  for (const letter of letters) {
    const row = document.createElement('button');
    row.type = 'button';
    row.className = 'queue-row';
    const icon = document.createElement('span');
    icon.className = 'queue-icon';
    const image = document.createElement('img');
    image.src = 'assets/icons/cassette-tape.svg';
    image.alt = '';
    icon.append(image);
    const copy = document.createElement('span');
    copy.className = 'queue-copy';
    const title = document.createElement('span');
    title.className = 'queue-title';
    title.textContent = displayName(letter.source);
    const subtitle = document.createElement('span');
    subtitle.className = 'queue-subtitle';
    subtitle.textContent = purposeFor(letter);
    copy.append(title, subtitle);
    const meta = document.createElement('span');
    meta.className = 'queue-meta';
    const time = document.createElement('span');
    time.className = 'queue-time';
    time.textContent = relativeTime(letter.created_at);
    const chevron = document.createElement('img');
    chevron.className = 'queue-chevron';
    chevron.src = 'assets/icons/caret-right.svg';
    chevron.alt = '';
    meta.append(time, chevron);
    row.append(icon, copy, meta);
    row.addEventListener('click', () => showToast('Voice playback will arrive with the SimpleX transport.'));
    list.append(row);
  }
}

function renderAdapters() {
  const list = $('adapters');
  list.replaceChildren();
  const adapters = Object.values(state.status?.adapters || {});
  if (!adapters.length) {
    const item = document.createElement('li');
    item.textContent = 'Connect to check the line.';
    list.append(item);
    return;
  }
  for (const adapter of adapters) {
    const item = document.createElement('li');
    const name = document.createElement('strong');
    name.textContent = displayName(adapter.name);
    item.append(name, ` — ${adapter.ready ? 'ready' : adapter.detail}`);
    list.append(item);
  }
}

function render() {
  renderHome();
  renderLetters();
  renderAdapters();
}

async function refresh({ quiet = false } = {}) {
  if (state.refreshInFlight) return true;
  if (previewMode) {
    const data = previewData();
    state.status = data.status;
    state.sessions = data.sessions;
    setLine(true, 'Line open');
    $('connection').textContent = 'Preview line connected';
    render();
    return true;
  }
  if (!token()) {
    teardownAudio();
    state.status = null;
    state.sessions = [];
    state.connectedToken = null;
    setLine(false, 'Private line');
    $('connection').textContent = 'Not connected';
    render();
    return false;
  }
  const requestToken = token();
  state.refreshInFlight = true;
  try {
    const [status, inbox] = await Promise.all([call('status'), call('inbox')]);
    if (requestToken !== token()) return false;
    reconcileAudio(inbox.sessions);
    state.status = status;
    state.sessions = inbox.sessions;
    state.connectedToken = requestToken;
    state.authFailed = false;
    state.backoff = 4000;
    setLine(true, 'Line open');
    $('connection').textContent = 'Connected to your private line';
    render();
    return true;
  } catch (error) {
    state.authFailed = error.status === 401;
    if (state.authFailed) {
      teardownAudio();
      state.connectedToken = null;
    }
    state.backoff = Math.min(state.backoff * 2, 60000);
    setLine(false, state.authFailed ? 'Connection key needed' : 'Line unavailable');
    $('connection').textContent = error.message;
    if (!quiet) showToast(error.message);
    return false;
  } finally {
    state.refreshInFlight = false;
  }
}

async function transitionSelected(nextState) {
  const session = state.sessions.find((item) => item.id === state.selectedId);
  if (!session) return false;
  if (previewMode) {
    session.state = nextState;
    if (nextState === 'deferred') state.selectedId = null;
    render();
    showToast(nextState === 'accepted' ? 'Call accepted in preview.' : 'Kept quietly for later.');
    return true;
  }
  try {
    const result = await call(`sessions/${encodeURIComponent(session.id)}/transition`, {
      method: 'POST',
      body: JSON.stringify({ state: nextState }),
    });
    session.state = result.state;
    if (nextState === 'deferred') state.selectedId = null;
    render();
    if (nextState === 'accepted') await prepareAudio(session.id);
    else showToast('Kept quietly for later.');
    return true;
  } catch (error) {
    $('call-state').textContent = error.message;
    return false;
  }
}

async function prepareAudio(id) {
  if (state.audio.sessionId === id) {
    if (state.audio.setupPromise) return state.audio.setupPromise;
    if (audioIsOpenFor(id)) return true;
    teardownAudio();
  } else if (state.audio.sessionId) {
    teardownAudio();
  }

  const epoch = state.audio.epoch + 1;
  state.audio.epoch = epoch;
  state.audio.sessionId = id;
  $('call-state').textContent = 'Requesting microphone access…';

  const setupPromise = (async () => {
    let stream = null;
    let peer = null;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
      if (!audioSetupIsCurrent(epoch, id)) {
        for (const track of stream.getTracks()) track.stop();
        return false;
      }

      state.audio.stream = stream;
      peer = new RTCPeerConnection();
      state.audio.peer = peer;
      window.olgalPeer = peer;
      for (const track of stream.getTracks()) peer.addTrack(track, stream);

      peer.onicecandidate = (event) => {
        if (!event.candidate || !audioSetupIsCurrent(epoch, id)) return;
        call(`sessions/${encodeURIComponent(id)}/signals`, {
          method: 'POST',
          body: JSON.stringify({ payload: { type: 'ice', candidate: event.candidate } }),
        }).catch((error) => {
          if (audioSetupIsCurrent(epoch, id)) {
            $('call-state').textContent = `Private audio needs attention: ${error.message}`;
          }
        });
      };
      peer.onconnectionstatechange = () => {
        if (!audioSetupIsCurrent(epoch, id)) return;
        if (peer.connectionState === 'connected') {
          $('call-state').textContent = 'Private audio connected';
        } else if (peer.connectionState === 'failed') {
          teardownAudio('Private audio connection closed.');
          renderHome();
        }
      };

      const offer = await peer.createOffer();
      if (!audioSetupIsCurrent(epoch, id)) return false;
      await peer.setLocalDescription(offer);
      if (!audioSetupIsCurrent(epoch, id)) return false;
      await call(`sessions/${encodeURIComponent(id)}/signals`, {
        method: 'POST',
        body: JSON.stringify({ payload: { type: 'offer', sdp: offer.sdp } }),
      });
      if (!audioSetupIsCurrent(epoch, id)) return false;
      $('call-state').textContent = 'Microphone ready · waiting for the private peer';
      return true;
    } catch (error) {
      if (audioSetupIsCurrent(epoch, id)) {
        teardownAudio(`Call accepted, but audio needs attention: ${error.message}`);
        renderHome();
      } else {
        if (peer && peer.signalingState !== 'closed') peer.close();
        for (const track of stream?.getTracks() || []) track.stop();
      }
      return false;
    } finally {
      if (state.audio.epoch === epoch) {
        state.audio.setupPromise = null;
        renderHome();
      }
    }
  })();
  state.audio.setupPromise = setupPromise;
  renderHome();
  return setupPromise;
}

async function endSelectedCall() {
  if (state.endInFlight) return;
  const session = state.sessions.find((item) => item.id === state.selectedId);
  if (!isLiveCallSession(session)) return;

  state.endInFlight = true;
  if (state.audio.sessionId === session.id) teardownAudio('Closing the microphone…');
  renderHome();

  if (previewMode) {
    session.state = 'ended';
    state.sessions = state.sessions.filter((item) => item.id !== session.id);
    state.selectedId = null;
    state.endInFlight = false;
    render();
    showToast('Call ended in preview.');
    return;
  }

  try {
    const result = await call(`sessions/${encodeURIComponent(session.id)}/end`, {
      method: 'POST',
      body: JSON.stringify({}),
    });
    session.state = result.state;
    state.sessions = state.sessions.filter((item) => item.id !== session.id);
    state.selectedId = null;
    $('call-state').textContent = '';
    showToast('Call ended. The microphone is off.');
  } catch (error) {
    $('call-state').textContent = `Microphone off · ${error.message}`;
    showToast('The microphone is off, but OlGal could not confirm the call ended.');
  } finally {
    state.endInFlight = false;
    render();
  }
}

function showView(view) {
  if (view !== 'home' && state.audio.sessionId) {
    teardownAudio('Microphone paused when you left the call screen.');
    renderHome();
    showToast('The microphone is off until you reopen the call.');
  }
  state.view = view;
  $('home-view').hidden = view !== 'home';
  $('letters-view').hidden = view !== 'letters';
  for (const button of document.querySelectorAll('[data-view]')) {
    const active = button.dataset.view === view;
    button.classList.toggle('active', active);
    if (active) button.setAttribute('aria-current', 'page');
    else button.removeAttribute('aria-current');
  }
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

let toastTimer;
function showToast(message) {
  clearTimeout(toastTimer);
  $('toast').textContent = message;
  $('toast').hidden = false;
  toastTimer = setTimeout(() => { $('toast').hidden = true; }, 3200);
}

function openSettings() {
  if (state.audio.sessionId) {
    teardownAudio('Microphone paused while Settings is open.');
    renderHome();
  }
  if (!$('settings-dialog').open) $('settings-dialog').showModal();
}

function scheduleRefresh() {
  clearTimeout(state.refreshTimer);
  if (previewMode || state.authFailed || document.hidden) return;
  state.refreshTimer = setTimeout(async () => {
    await refresh({ quiet: true });
    scheduleRefresh();
  }, state.backoff);
}

for (const button of document.querySelectorAll('[data-open-settings]')) button.addEventListener('click', openSettings);
for (const button of document.querySelectorAll('[data-view]')) button.addEventListener('click', () => showView(button.dataset.view));

$('close-settings').addEventListener('click', () => $('settings-dialog').close());
$('settings-dialog').addEventListener('click', (event) => {
  if (event.target === $('settings-dialog')) $('settings-dialog').close();
});

$('save').addEventListener('click', async () => {
  const nextToken = token();
  if (state.connectedToken && state.connectedToken !== nextToken) {
    teardownAudio('Microphone closed while this device reconnects.');
  }
  localStorage.removeItem('olgal-comms-token');
  sessionStorage.removeItem('olgal-comms-token');
  if (nextToken) ($('remember-token').checked ? localStorage : sessionStorage).setItem('olgal-comms-token', nextToken);
  state.authFailed = false;
  const connected = await refresh();
  scheduleRefresh();
  if (connected) {
    $('settings-dialog').close();
    showToast('The Hearth is connected.');
  }
});

$('clear-token').addEventListener('click', () => {
  teardownAudio();
  localStorage.removeItem('olgal-comms-token');
  sessionStorage.removeItem('olgal-comms-token');
  $('token').value = '';
  state.status = null;
  state.sessions = [];
  state.connectedToken = null;
  state.authFailed = false;
  setLine(false, 'Private line');
  render();
  $('connection').textContent = 'Connection key forgotten on this device';
  scheduleRefresh();
});

$('token').addEventListener('input', () => {
  if (state.audio.sessionId && token() !== state.connectedToken) {
    teardownAudio('Microphone closed until this device reconnects.');
    renderHome();
  }
});

$('answer').addEventListener('click', async () => {
  if (state.answerInFlight || state.endInFlight) return;
  const selected = state.sessions.find((item) => item.id === state.selectedId);
  if (!selected) return;
  if (state.audio.sessionId === selected.id
      && (state.audio.setupPromise || audioIsOpenFor(selected.id))) return;
  state.answerInFlight = true;
  renderHome();
  try {
    if (LIVE_CALL_STATES.has(selected.state) && !previewMode) await prepareAudio(selected.id);
    else await transitionSelected('accepted');
  } finally {
    state.answerInFlight = false;
    renderHome();
  }
});
$('later').addEventListener('click', () => {
  if (!state.answerInFlight && !state.endInFlight) transitionSelected('deferred');
});
$('hangup').addEventListener('click', endSelectedCall);
document.addEventListener('visibilitychange', () => {
  if (document.hidden) {
    if (state.audio.sessionId) {
      teardownAudio('Microphone paused while the Hearth is hidden.');
      renderHome();
    }
    scheduleRefresh();
  } else if (!state.authFailed) {
    refresh({ quiet: true }).then(scheduleRefresh);
  }
});
window.addEventListener('pagehide', () => teardownAudio());
window.addEventListener('beforeunload', () => teardownAudio());

if ('serviceWorker' in navigator && !previewMode) navigator.serviceWorker.register('sw.js');
refresh().then(scheduleRefresh);
