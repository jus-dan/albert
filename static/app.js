const PERSONA_NAMES = { albert: "Albert", albertine: "Albertine", alex: "Alex" };
const SAMPLE_RATE = 24000;

const personaSelect = document.getElementById("persona-select");
const conversation = document.getElementById("conversation");
const personaHeading = document.getElementById("persona-heading");
const statusBadge = document.getElementById("status-badge");
const statusText = document.getElementById("status-text");
const toggleButton = document.getElementById("toggle-button");
const micWarning = document.getElementById("mic-warning");
const micIndicator = document.getElementById("mic-indicator");
const chatLog = document.getElementById("chat-log");
const backButton = document.getElementById("back-button");

let currentPersonaId = null;
let socket = null;
let audioContext = null;
let micStream = null;
let micSource = null;
let micProcessor = null;
let micReady = false;
let isActive = false;
let playhead = 0;
let activeSources = [];
let pendingUserBubbles = [];
let currentAssistantBubble = null;
let currentReveal = null;

const REVEAL_CHARS_PER_SEC = 24;

setInterval(() => {
  if (!currentReveal) return;
  const elapsedSec = (performance.now() - currentReveal.startedAt) / 1000;
  const target = Math.min(currentReveal.fullText.length, Math.floor(elapsedSec * REVEAL_CHARS_PER_SEC));
  if (target > currentReveal.revealed) {
    currentReveal.revealed = target;
    if (currentReveal.bubble.isConnected) {
      currentReveal.bubble.textContent = currentReveal.fullText.slice(0, target);
      chatLog.scrollTop = chatLog.scrollHeight;
    }
  }
}, 50);

function setStatus(state, text) {
  statusBadge.className = `status status-${state}`;
  statusText.textContent = text;
}

function addMessage(role, text) {
  const bubble = document.createElement("div");
  bubble.className = `message message-${role}`;
  bubble.textContent = text;
  chatLog.appendChild(bubble);
  chatLog.scrollTop = chatLog.scrollHeight;
  return bubble;
}

function flushReveal() {
  if (currentReveal && currentReveal.bubble.isConnected) {
    currentReveal.bubble.textContent = currentReveal.fullText;
    chatLog.scrollTop = chatLog.scrollHeight;
  }
  currentReveal = null;
}

function startReveal(bubble) {
  flushReveal();
  currentReveal = { bubble, fullText: "", revealed: 0, startedAt: performance.now() };
}

function appendRevealText(delta) {
  if (currentReveal) {
    currentReveal.fullText += delta;
  }
}

const ENTITY_TYPE_LABELS = {
  initiative: "Initiative",
  organization: "Organisation",
  person: "Person",
  future_wish: "Zukunftswunsch",
  challenge: "Challenge",
};

function addEntryNotice(message) {
  const notice = document.createElement("div");
  notice.className = "entry-notice";
  const typeLabel = ENTITY_TYPE_LABELS[message.entity_type] || message.entity_type;
  notice.textContent = `Neuer Eintrag erfasst: "${message.name}" (${typeLabel})`;
  chatLog.appendChild(notice);
  chatLog.scrollTop = chatLog.scrollHeight;
}

function addPrintLink(recordId) {
  const link = document.createElement("a");
  link.href = `/wunschzettel.html?id=${encodeURIComponent(recordId)}`;
  link.target = "_blank";
  link.rel = "noopener";
  link.className = "print-link";
  link.textContent = "🖨️ Wunschzettel ansehen & ausdrucken";
  chatLog.appendChild(link);
  chatLog.scrollTop = chatLog.scrollHeight;
}

function floatTo16BitPCM(float32Array) {
  const out = new Int16Array(float32Array.length);
  for (let i = 0; i < float32Array.length; i++) {
    const s = Math.max(-1, Math.min(1, float32Array[i]));
    out[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }
  return out;
}

function arrayBufferToBase64(buffer) {
  let binary = "";
  const bytes = new Uint8Array(buffer);
  const chunkSize = 0x8000;
  for (let i = 0; i < bytes.length; i += chunkSize) {
    binary += String.fromCharCode.apply(null, bytes.subarray(i, i + chunkSize));
  }
  return btoa(binary);
}

function base64ToInt16(base64) {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return new Int16Array(bytes.buffer);
}

function playAudioChunk(int16Array) {
  const float32 = new Float32Array(int16Array.length);
  for (let i = 0; i < int16Array.length; i++) {
    float32[i] = int16Array[i] / 0x8000;
  }
  const audioBuffer = audioContext.createBuffer(1, float32.length, SAMPLE_RATE);
  audioBuffer.copyToChannel(float32, 0);

  const source = audioContext.createBufferSource();
  source.buffer = audioBuffer;
  source.connect(audioContext.destination);
  source.onended = () => {
    activeSources = activeSources.filter((s) => s !== source);
  };
  activeSources.push(source);

  const startAt = Math.max(playhead, audioContext.currentTime);
  source.start(startAt);
  playhead = startAt + audioBuffer.duration;
}

function stopAllAudio() {
  activeSources.forEach((source) => {
    try {
      source.stop();
    } catch (err) {
      /* already stopped */
    }
  });
  activeSources = [];
}

function stopPlaybackForBargeIn() {
  stopAllAudio();
  if (audioContext) {
    playhead = audioContext.currentTime;
  }
}

function connectSocket(personaId) {
  const protocol = location.protocol === "https:" ? "wss" : "ws";
  socket = new WebSocket(`${protocol}://${location.host}/ws/${personaId}`);

  socket.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);

    if (message.type === "status" && message.status === "ready") {
      setStatus("active", `${message.persona} ist aktiv`);
    } else if (message.type === "audio") {
      playAudioChunk(base64ToInt16(message.audio));
    } else if (message.type === "assistant_start") {
      currentAssistantBubble = addMessage("assistant", "");
      startReveal(currentAssistantBubble);
    } else if (message.type === "transcript") {
      if (!currentAssistantBubble) {
        currentAssistantBubble = addMessage("assistant", "");
        startReveal(currentAssistantBubble);
      }
      appendRevealText(message.delta);
    } else if (message.type === "user_message") {
      const bubble = pendingUserBubbles.shift();
      if (bubble) {
        bubble.textContent = message.text;
      } else {
        addMessage("user", message.text);
      }
    } else if (message.type === "new_entry") {
      addEntryNotice(message);
    } else if (message.type === "print_link") {
      addPrintLink(message.record_id);
    } else if (message.type === "user_speaking") {
      stopPlaybackForBargeIn();
      pendingUserBubbles.push(addMessage("user", "…"));
    } else if (message.type === "error") {
      setStatus("error", message.message || "Fehler");
    }
  });

  socket.addEventListener("close", () => {
    if (isActive) {
      setStatus("error", "Getrennt");
      stopSession();
    }
  });
  socket.addEventListener("error", () => setStatus("error", "Verbindungsfehler"));
}

async function setupMic() {
  try {
    micStream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
    });
  } catch (err) {
    micWarning.hidden = false;
    return;
  }

  micSource = audioContext.createMediaStreamSource(micStream);
  micProcessor = audioContext.createScriptProcessor(4096, 1, 1);
  const silentGain = audioContext.createGain();
  silentGain.gain.value = 0;

  micProcessor.onaudioprocess = (event) => {
    if (!isActive || !socket || socket.readyState !== WebSocket.OPEN) return;
    const input = event.inputBuffer.getChannelData(0);
    const pcm16 = floatTo16BitPCM(input);
    socket.send(JSON.stringify({ type: "audio_chunk", audio: arrayBufferToBase64(pcm16.buffer) }));
  };

  micSource.connect(micProcessor);
  micProcessor.connect(silentGain);
  silentGain.connect(audioContext.destination);
  micReady = true;
  micIndicator.hidden = false;
}

function stopMicCapture() {
  micReady = false;
  if (micProcessor) {
    micProcessor.disconnect();
    micProcessor.onaudioprocess = null;
    micProcessor = null;
  }
  if (micSource) {
    micSource.disconnect();
    micSource = null;
  }
  if (micStream) {
    micStream.getTracks().forEach((track) => track.stop());
    micStream = null;
  }
}

async function startSession() {
  if (isActive || !currentPersonaId) return;
  isActive = true;
  toggleButton.textContent = "Stop";
  toggleButton.classList.remove("toggle-start");
  toggleButton.classList.add("toggle-stop");
  micWarning.hidden = true;
  setStatus("connecting", "Verbinde ...");

  audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: SAMPLE_RATE });
  try {
    await audioContext.resume();
  } catch (err) {
    /* ignore */
  }
  playhead = audioContext.currentTime;
  currentAssistantBubble = null;
  currentReveal = null;
  pendingUserBubbles = [];

  connectSocket(currentPersonaId);
  setupMic();
}

function stopSession() {
  isActive = false;
  toggleButton.textContent = "Start";
  toggleButton.classList.remove("toggle-stop");
  toggleButton.classList.add("toggle-start");
  micIndicator.hidden = true;
  flushReveal();

  if (socket) {
    socket.close();
    socket = null;
  }
  stopAllAudio();
  stopMicCapture();
  if (audioContext) {
    audioContext.close();
    audioContext = null;
  }
  setStatus("inactive", "Inaktiv");
}

function selectPersona(personaId) {
  currentPersonaId = personaId;
  personaHeading.textContent = PERSONA_NAMES[personaId] ?? personaId;
  personaSelect.hidden = true;
  conversation.hidden = false;
  chatLog.innerHTML = "";
  micWarning.hidden = true;
  micIndicator.hidden = true;
  setStatus("inactive", "Inaktiv");
}

document.querySelectorAll(".persona-card").forEach((btn) => {
  btn.addEventListener("click", () => selectPersona(btn.dataset.persona));
});

toggleButton.addEventListener("click", () => {
  if (isActive) {
    stopSession();
  } else {
    startSession();
  }
});

backButton.addEventListener("click", () => {
  stopSession();
  currentPersonaId = null;
  conversation.hidden = true;
  personaSelect.hidden = false;
});
