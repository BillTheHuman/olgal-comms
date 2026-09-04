const api = 'api/v1';
const $ = (id) => document.getElementById(id);
const token = () => $('token').value.trim();

async function call(path, options = {}) {
  const response = await fetch(`${api}/${path}`, {
    ...options,
    headers: { 'Authorization': `Bearer ${token()}`, 'Content-Type': 'application/json', ...(options.headers || {}) },
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || `Request failed (${response.status})`);
  return body;
}

async function refresh() {
  try {
    const data = await call('status');
    $('connection').textContent = `Connected · recipient: ${data.recipient}`;
    const adapters = $('adapters');
    adapters.replaceChildren();
    for (const adapter of Object.values(data.adapters)) {
      const item = document.createElement('li');
      const name = document.createElement('strong');
      name.textContent = adapter.name;
      if (adapter.ready) name.classList.add('ready');
      const boundary = document.createElement('small');
      boundary.textContent = adapter.privacy_boundary;
      item.append(name, ` — ${adapter.ready ? 'ready' : adapter.detail}`, document.createElement('br'), boundary);
      adapters.append(item);
    }
  } catch (error) { $('connection').textContent = error.message; }
}

async function transition(state) {
  const id = $('session').value.trim();
  if (!id) return void ($('call-state').textContent = 'Enter a session ID.');
  try {
    const result = await call(`sessions/${encodeURIComponent(id)}/transition`, { method: 'POST', body: JSON.stringify({ state }) });
    $('call-state').textContent = `Session ${result.state}`;
    if (state === 'accepted') await prepareAudio(id);
  } catch (error) { $('call-state').textContent = error.message; }
}

async function prepareAudio(id) {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
    const pc = new RTCPeerConnection();
    stream.getTracks().forEach(track => pc.addTrack(track, stream));
    pc.onicecandidate = async event => {
      if (event.candidate) await call(`sessions/${encodeURIComponent(id)}/signals`, {
        method: 'POST', body: JSON.stringify({ sender: 'self', payload: { type: 'ice', candidate: event.candidate } }),
      });
    };
    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);
    await call(`sessions/${encodeURIComponent(id)}/signals`, {
      method: 'POST', body: JSON.stringify({ sender: 'self', payload: { type: 'offer', sdp: offer.sdp } }),
    });
    window.olgalPeer = pc;
    $('call-state').textContent = 'Accepted · microphone ready · waiting for peer';
  } catch (error) { $('call-state').textContent = `Accepted, but audio failed: ${error.message}`; }
}

$('token').value = localStorage.getItem('olgal-comms-token') || '';
$('save').onclick = () => { localStorage.setItem('olgal-comms-token', token()); refresh(); };
$('refresh').onclick = refresh;
$('accept').onclick = () => transition('accepted');
$('decline').onclick = () => transition('declined');
$('hangup').onclick = () => transition('ended');
if ('serviceWorker' in navigator) navigator.serviceWorker.register('sw.js');
if (token()) refresh();
