/**
 * ಕನ್ನಡ ಲಿಪಿ ಮಿತ್ರ (Kannada Lipi Mitra) — Frontend Controller
 * Engine-Agnostic Kannada Document AI, Split-View OCR, In-text Search, Meaning & Speech
 */

// Configuration
// Local dev (Vite on :5173) proxies API to the FastAPI backend on :8000.
// Anywhere else (backend-served production build, deployed URL) use same origin.
const IS_LOCAL_DEV = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
  && window.location.port === '5173';
const API_BASE_URL = IS_LOCAL_DEV ? 'http://127.0.0.1:8000' : window.location.origin;

// State Management
const state = {
  currentFile: null,
  currentFileName: '',
  extractedText: '',
  activeEngine: 'groq',
  zoomLevel: 1.0,
  isOcrLoading: false,
  isTranslating: false,
  isTtsLoading: false,
  isPlayingAudio: false,
  lastAction: null, // For retry on error / 429
  retryTimer: null,
  activeSample: null
};

// DOM Elements
const elements = {
  // Inputs
  fileUploadInput: document.getElementById('fileUploadInput'),
  cameraUploadInput: document.getElementById('cameraUploadInput'),
  uploadBtn: document.getElementById('uploadBtn'),
  cameraBtn: document.getElementById('cameraBtn'),
  samplePills: document.querySelectorAll('.sample-pill'),

  // Alerts & Banners
  rateLimitBanner: document.getElementById('rateLimitBanner'),
  rateLimitMsg: document.getElementById('rateLimitMsg'),
  retryCountdown: document.getElementById('retryCountdown'),
  rateLimitRetryBtn: document.getElementById('rateLimitRetryBtn'),
  generalErrorBanner: document.getElementById('generalErrorBanner'),
  generalErrorTitle: document.getElementById('generalErrorTitle'),
  generalErrorMsg: document.getElementById('generalErrorMsg'),
  errorDismissBtn: document.getElementById('errorDismissBtn'),
  errorRetryBtn: document.getElementById('errorRetryBtn'),
  scriptWarningBanner: document.getElementById('scriptWarningBanner'),
  scriptWarningMsg: document.getElementById('scriptWarningMsg'),
  scriptWarningDismissBtn: document.getElementById('scriptWarningDismissBtn'),
  engineStatusBadge: document.getElementById('engineStatusBadge'),
  engineBadgeText: document.getElementById('engineBadgeText'),

  // Left Pane: Image & Zoom
  imageDocName: document.getElementById('imageDocName'),
  uploadDropzone: document.getElementById('uploadDropzone'),
  previewImage: document.getElementById('previewImage'),
  imageViewport: document.getElementById('imageViewport'),
  zoomControls: document.getElementById('zoomControls'),
  zoomInBtn: document.getElementById('zoomInBtn'),
  zoomOutBtn: document.getElementById('zoomOutBtn'),
  zoomResetBtn: document.getElementById('zoomResetBtn'),
  zoomLevelDisplay: document.getElementById('zoomLevelDisplay'),
  ocrLoadingOverlay: document.getElementById('ocrLoadingOverlay'),
  loadingStepTitle: document.getElementById('loadingStepTitle'),
  loadingStepSub: document.getElementById('loadingStepSub'),

  // Right Pane: Editor & Search
  kannadaEditor: document.getElementById('kannadaEditor'),
  searchBackdrop: document.getElementById('searchBackdrop'),
  inTextSearchInput: document.getElementById('inTextSearchInput'),
  clearSearchBtn: document.getElementById('clearSearchBtn'),
  searchMatchCount: document.getElementById('searchMatchCount'),
  wordCountDisplay: document.getElementById('wordCountDisplay'),
  charCountDisplay: document.getElementById('charCountDisplay'),
  engineUsedStat: document.getElementById('engineUsedStat'),
  engineUsedDisplay: document.getElementById('engineUsedDisplay'),

  // Action Suite
  readAloudBtn: document.getElementById('readAloudBtn'),
  readAloudBtnText: document.getElementById('readAloudBtnText'),
  copyTextBtn: document.getElementById('copyTextBtn'),
  exportTxtBtn: document.getElementById('exportTxtBtn'),
  printPdfBtn: document.getElementById('printPdfBtn'),

  // TTS Player
  ttsPlayerBar: document.getElementById('ttsPlayerBar'),
  ttsAudioElement: document.getElementById('ttsAudioElement'),
  ttsPlayPauseBtn: document.getElementById('ttsPlayPauseBtn'),
  playIcon: document.getElementById('playIcon'),
  pauseIcon: document.getElementById('pauseIcon'),
  audioProgressBar: document.getElementById('audioProgressBar'),
  audioTimeDisplay: document.getElementById('audioTimeDisplay'),
  audioModeBadge: document.getElementById('audioModeBadge'),

  // Translation Panel
  translateEnBtn: document.getElementById('translateEnBtn'),
  translateHiBtn: document.getElementById('translateHiBtn'),
  translationContent: document.getElementById('translationContent'),
  translationLangTag: document.getElementById('translationLangTag'),
  translationOutputText: document.getElementById('translationOutputText'),
  copyTranslationBtn: document.getElementById('copyTranslationBtn'),

  // Toast & Print Header
  toastNotification: document.getElementById('toastNotification'),
  toastMessage: document.getElementById('toastMessage'),
  printHeader: document.getElementById('printHeader'),
  printTimestamp: document.getElementById('printTimestamp'),
  printMetaInfo: document.getElementById('printMetaInfo')
};

// ==============================================================================
// 1. Initialization & Backend Health Check
// ==============================================================================
async function initApp() {
  bindEvents();
  await checkBackendHealth();
  updateCounters();
}

async function checkBackendHealth() {
  try {
    const res = await fetch(`${API_BASE_URL}/api/health`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    
    state.activeEngine = data.active_engine || 'groq';
    const isReady = data.active_engine_ready;
    const model = data.engines?.[state.activeEngine]?.vision_model || state.activeEngine.toUpperCase();
    
    elements.engineBadgeText.textContent = `${state.activeEngine.toUpperCase()}: ${isReady ? 'READY' : 'CONFIG REQUIRED'}`;
    elements.engineStatusBadge.style.color = isReady ? '#34d399' : '#f87171';
    elements.engineStatusBadge.style.borderColor = isReady ? 'rgba(16, 185, 129, 0.4)' : 'rgba(239, 68, 68, 0.4)';
  } catch (err) {
    elements.engineBadgeText.textContent = 'Backend Offline';
    elements.engineStatusBadge.style.color = '#f87171';
    elements.engineStatusBadge.style.borderColor = 'rgba(239, 68, 68, 0.4)';
  }
}

// ==============================================================================
// 2. Event Listeners & Binding
// ==============================================================================
function bindEvents() {
  // Upload & Camera Trigger
  elements.uploadBtn.addEventListener('click', () => elements.fileUploadInput.click());
  elements.cameraBtn.addEventListener('click', () => elements.cameraUploadInput.click());

  elements.fileUploadInput.addEventListener('change', (e) => {
    if (e.target.files?.length > 0) handleFileSelection(e.target.files[0]);
  });

  elements.cameraUploadInput.addEventListener('change', (e) => {
    if (e.target.files?.length > 0) handleFileSelection(e.target.files[0]);
  });

  // Drag and Drop
  const dropzone = elements.uploadDropzone;
  dropzone.addEventListener('click', () => elements.fileUploadInput.click());
  
  ['dragenter', 'dragover'].forEach(name => {
    dropzone.addEventListener(name, (e) => {
      e.preventDefault();
      dropzone.classList.add('drag-active');
    });
  });

  ['dragleave', 'drop'].forEach(name => {
    dropzone.addEventListener(name, (e) => {
      e.preventDefault();
      dropzone.classList.remove('drag-active');
    });
  });

  dropzone.addEventListener('drop', (e) => {
    if (e.dataTransfer.files?.length > 0) {
      handleFileSelection(e.dataTransfer.files[0]);
    }
  });

  // Sample Documents Quick Picker
  elements.samplePills.forEach(pill => {
    pill.addEventListener('click', () => {
      const filename = pill.getAttribute('data-filename');
      const title = pill.getAttribute('data-title');
      loadSampleDocument(filename, title, pill);
    });
  });

  // Image Zoom Controls
  elements.zoomInBtn.addEventListener('click', () => adjustZoom(0.2));
  elements.zoomOutBtn.addEventListener('click', () => adjustZoom(-0.2));
  elements.zoomResetBtn.addEventListener('click', () => setZoom(1.0));

  // Editor Input & Word/Char Counter
  elements.kannadaEditor.addEventListener('input', () => {
    state.extractedText = elements.kannadaEditor.value;
    updateCounters();
    syncSearchHighlights();
  });

  elements.kannadaEditor.addEventListener('scroll', () => {
    elements.searchBackdrop.scrollTop = elements.kannadaEditor.scrollTop;
  });

  // In-Text Search
  elements.inTextSearchInput.addEventListener('input', syncSearchHighlights);
  elements.clearSearchBtn.addEventListener('click', () => {
    elements.inTextSearchInput.value = '';
    syncSearchHighlights();
  });

  // Action Suite
  elements.copyTextBtn.addEventListener('click', copyExtractedText);
  elements.exportTxtBtn.addEventListener('click', exportAsTxt);
  elements.printPdfBtn.addEventListener('click', triggerPrintPdf);
  elements.readAloudBtn.addEventListener('click', toggleReadAloud);

  // Translation Triggers
  elements.translateEnBtn.addEventListener('click', () => requestTranslation('en'));
  elements.translateHiBtn.addEventListener('click', () => requestTranslation('hi'));
  elements.copyTranslationBtn.addEventListener('click', copyTranslationText);

  // Error & 429 Actions
  elements.rateLimitRetryBtn.addEventListener('click', executeRetry);
  elements.errorRetryBtn.addEventListener('click', executeRetry);
  elements.errorDismissBtn.addEventListener('click', dismissErrors);
  elements.scriptWarningDismissBtn.addEventListener('click', () => {
    elements.scriptWarningBanner.style.display = 'none';
  });

  // TTS Audio Player controls
  elements.ttsPlayPauseBtn.addEventListener('click', toggleAudioPlayback);
  elements.ttsAudioElement.addEventListener('timeupdate', updateAudioProgress);
  elements.ttsAudioElement.addEventListener('ended', onAudioEnded);
}

// ==============================================================================
// 3. File & Sample Handling
// ==============================================================================
function handleFileSelection(file) {
  if (!file.type.startsWith('image/')) {
    showGeneralError('ಅಮಾನ್ಯ ಕಡತ / Invalid File', 'Please select a valid image file (PNG, JPG, or WEBP).');
    return;
  }

  dismissErrors();
  state.currentFile = file;
  state.currentFileName = file.name;
  elements.imageDocName.textContent = file.name;

  // Unset active sample badge
  elements.samplePills.forEach(p => p.classList.remove('active'));

  // Display image preview
  const reader = new FileReader();
  reader.onload = (e) => {
    showPreviewImage(e.target.result);
  };
  reader.readAsDataURL(file);

  // Trigger OCR extraction
  triggerOcrExtraction(file);
}

async function loadSampleDocument(filename, title, pillElement) {
  dismissErrors();
  elements.samplePills.forEach(p => p.classList.remove('active'));
  pillElement.classList.add('active');

  state.activeSample = filename;
  state.currentFileName = `SAMPLE (generated): ${title}`;
  elements.imageDocName.textContent = state.currentFileName;

  const sampleUrl = `/samples/${filename}`;

  try {
    // Show preview immediately
    showPreviewImage(sampleUrl);

    // Fetch the sample image as a Blob to submit to OCR
    const res = await fetch(sampleUrl);
    if (!res.ok) throw new Error(`Could not load ${sampleUrl}`);
    const blob = await res.blob();
    const file = new File([blob], filename, { type: blob.type || 'image/png' });

    state.currentFile = file;
    triggerOcrExtraction(file);
  } catch (err) {
    showGeneralError('Sample Load Error', `Failed to load sample document: ${err.message}`);
  }
}

function showPreviewImage(src) {
  elements.uploadDropzone.style.display = 'none';
  elements.previewImage.src = src;
  elements.previewImage.style.display = 'block';
  elements.zoomControls.style.display = 'flex';
  setZoom(1.0);
}

// ==============================================================================
// 4. OCR Extraction Engine Integration
// ==============================================================================
async function triggerOcrExtraction(file) {
  state.isOcrLoading = true;
  state.lastAction = () => triggerOcrExtraction(file);
  showOcrLoading('ಕನ್ನಡ ಲಿಪಿ ಹೊರತೆಗೆಯಲಾಗುತ್ತಿದೆ...', `Transcribing with ${state.activeEngine.toUpperCase()} vision AI...`);

  const formData = new FormData();
  formData.append('file', file);

  try {
    const res = await fetch(`${API_BASE_URL}/api/ocr`, {
      method: 'POST',
      body: formData
    });

    const data = await res.json();

    if (res.status === 429) {
      hideOcrLoading();
      showRateLimitError(data.detail?.message || 'API rate limit reached. Retrying automatically in 5 seconds...', 5);
      return;
    }

    if (!res.ok) {
      const errMsg = typeof data.detail === 'object' ? data.detail.message : data.detail;
      throw new Error(errMsg || `Server error (${res.status})`);
    }

    hideOcrLoading();
    dismissErrors();

    // Populate extracted text
    state.extractedText = data.text || '';
    elements.kannadaEditor.value = state.extractedText;
    updateCounters(data.word_count, data.char_count);

    if (data.engine_used) {
      elements.engineUsedDisplay.textContent = `${data.engine_used.toUpperCase()} (${data.model_used || ''})`;
      elements.engineUsedStat.style.display = 'flex';
    }

    syncSearchHighlights();

    if (data.warning) {
      elements.scriptWarningMsg.textContent = data.warning;
      elements.scriptWarningBanner.style.display = 'flex';
    } else {
      elements.scriptWarningBanner.style.display = 'none';
    }

    showToast('ಲಿಪಿ ಯಶಸ್ವಿಯಾಗಿ ಹೊರತೆಗೆಯಲಾಗಿದೆ (OCR Complete)');

    // Reset translation panel for new document
    elements.translationContent.style.display = 'none';
    elements.translateEnBtn.classList.remove('active');
    elements.translateHiBtn.classList.remove('active');

  } catch (err) {
    hideOcrLoading();
    showGeneralError('OCR Extraction Failed', err.message);
  } finally {
    state.isOcrLoading = false;
  }
}

// ==============================================================================
// 5. In-Text Search with Match Counter & Visual Highlight
// ==============================================================================
function syncSearchHighlights() {
  const query = elements.inTextSearchInput.value.trim();
  const text = elements.kannadaEditor.value;

  if (!query) {
    elements.clearSearchBtn.style.display = 'none';
    elements.searchMatchCount.textContent = '0 matches';
    elements.searchBackdrop.innerHTML = escapeHtml(text);
    return;
  }

  elements.clearSearchBtn.style.display = 'block';

  try {
    // Escape regex special chars
    const escapedQuery = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const regex = new RegExp(`(${escapedQuery})`, 'gi');
    const matches = text.match(regex);
    const count = matches ? matches.length : 0;

    elements.searchMatchCount.textContent = `${count} ${count === 1 ? 'match' : 'matches'}`;
    elements.searchMatchCount.style.color = count > 0 ? '#f59e0b' : '#94a3b8';

    // Highlight inside searchBackdrop layer
    const highlighted = escapeHtml(text).replace(
      new RegExp(`(${escapedQuery})`, 'gi'),
      '<mark>$1</mark>'
    );
    elements.searchBackdrop.innerHTML = highlighted;
  } catch (e) {
    elements.searchMatchCount.textContent = '0 matches';
  }
}

function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// ==============================================================================
// 6. Word & Character Counters
// ==============================================================================
function updateCounters(words, chars) {
  const text = elements.kannadaEditor.value;
  if (words !== undefined && chars !== undefined) {
    elements.wordCountDisplay.textContent = words;
    elements.charCountDisplay.textContent = chars;
    return;
  }
  const cleanWords = text.trim() ? text.trim().split(/\s+/).length : 0;
  elements.wordCountDisplay.textContent = cleanWords;
  elements.charCountDisplay.textContent = text.length;
}

// ==============================================================================
// 7. Meaning on Demand (English / Hindi Translation)
// ==============================================================================
async function requestTranslation(targetLang) {
  const text = elements.kannadaEditor.value.trim();
  if (!text) {
    showToast('ದಯವಿಟ್ಟು ಮೊದಲು ಪಠ್ಯವನ್ನು ಒದಗಿಸಿ (No text to translate)');
    return;
  }

  const isEn = targetLang === 'en';
  const triggerBtn = isEn ? elements.translateEnBtn : elements.translateHiBtn;
  const otherBtn = isEn ? elements.translateHiBtn : elements.translateEnBtn;

  triggerBtn.classList.add('active');
  otherBtn.classList.remove('active');
  triggerBtn.textContent = 'Translating...';

  state.isTranslating = true;
  state.lastAction = () => requestTranslation(targetLang);

  try {
    const res = await fetch(`${API_BASE_URL}/api/translate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, target_lang: targetLang })
    });

    const data = await res.json();

    if (res.status === 429) {
      showRateLimitError(data.detail?.message || 'Rate limit reached during translation. Please wait...', 4);
      return;
    }

    if (!res.ok) {
      const msg = typeof data.detail === 'object' ? data.detail.message : data.detail;
      throw new Error(msg || 'Translation failed');
    }

    dismissErrors();
    elements.translationLangTag.textContent = isEn ? 'English Meaning' : 'हिन्दी Meaning';
    elements.translationOutputText.textContent = data.translation;
    elements.translationContent.style.display = 'block';
    showToast(`${isEn ? 'English' : 'Hindi'} translation ready`);

  } catch (err) {
    showGeneralError('Translation Error', err.message);
  } finally {
    state.isTranslating = false;
    elements.translateEnBtn.textContent = 'English Meaning';
    elements.translateHiBtn.textContent = 'हिन्दी Meaning';
  }
}

function copyTranslationText() {
  const transText = elements.translationOutputText.textContent;
  if (!transText) return;
  navigator.clipboard.writeText(transText).then(() => {
    showToast('ಅರ್ಥ ನಕಲಿಸಲಾಗಿದೆ (Translation copied)');
  });
}

// ==============================================================================
// 8. Read-Aloud (Text-to-Speech)
// ==============================================================================
async function toggleReadAloud() {
  const text = elements.kannadaEditor.value.trim();
  if (!text) {
    showToast('ದಯವಿಟ್ಟು ಓದಲು ಪಠ್ಯವನ್ನು ಒದಗಿಸಿ (No text to read)');
    return;
  }

  // If already playing audio, pause it
  if (state.isPlayingAudio) {
    elements.ttsAudioElement.pause();
    window.speechSynthesis.cancel();
    setAudioPlayingState(false);
    return;
  }

  // Check if browser has native Kannada voice
  const synth = window.speechSynthesis;
  const voices = synth.getVoices();
  const kannadaVoice = voices.find(v => v.lang === 'kn' || v.lang === 'kn-IN');

  if (kannadaVoice) {
    // Native browser speech synthesis
    synth.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.voice = kannadaVoice;
    utterance.lang = 'kn-IN';
    utterance.rate = 0.95;

    utterance.onstart = () => {
      setAudioPlayingState(true);
      elements.audioModeBadge.textContent = 'Browser Kannada Voice';
      elements.ttsPlayerBar.style.display = 'block';
    };
    utterance.onend = () => setAudioPlayingState(false);
    utterance.onerror = () => setAudioPlayingState(false);

    synth.speak(utterance);
    return;
  }

  // Otherwise, stream authentic Kannada audio from Backend gTTS (/api/tts)
  await streamBackendTTS(text);
}

async function streamBackendTTS(text) {
  elements.readAloudBtnText.textContent = 'ತಯಾರಿಸಲಾಗುತ್ತಿದೆ... (Loading Audio)';
  state.isTtsLoading = true;

  try {
    const res = await fetch(`${API_BASE_URL}/api/tts`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: text.slice(0, 2500) })
    });

    if (!res.ok) throw new Error(`TTS server error (${res.status})`);

    const blob = await res.blob();
    const audioUrl = URL.createObjectURL(blob);
    
    elements.ttsAudioElement.src = audioUrl;
    elements.audioModeBadge.textContent = 'Native Kannada gTTS Voice';
    elements.ttsPlayerBar.style.display = 'block';
    
    await elements.ttsAudioElement.play();
    setAudioPlayingState(true);
  } catch (err) {
    showGeneralError('Audio Playback Error', err.message);
  } finally {
    state.isTtsLoading = false;
    elements.readAloudBtnText.textContent = state.isPlayingAudio ? 'ನಿಲ್ಲಿಸಿ (Stop)' : 'ಓದಿ ಕೇಳಿ (Read Aloud)';
  }
}

function toggleAudioPlayback() {
  if (elements.ttsAudioElement.paused) {
    elements.ttsAudioElement.play();
    setAudioPlayingState(true);
  } else {
    elements.ttsAudioElement.pause();
    setAudioPlayingState(false);
  }
}

function updateAudioProgress() {
  const audio = elements.ttsAudioElement;
  if (!audio.duration) return;
  const pct = (audio.currentTime / audio.duration) * 100;
  elements.audioProgressBar.style.width = `${pct}%`;
  elements.audioTimeDisplay.textContent = `${formatTime(audio.currentTime)} / ${formatTime(audio.duration)}`;
}

function onAudioEnded() {
  setAudioPlayingState(false);
  elements.audioProgressBar.style.width = '0%';
}

function setAudioPlayingState(isPlaying) {
  state.isPlayingAudio = isPlaying;
  elements.playIcon.style.display = isPlaying ? 'none' : 'block';
  elements.pauseIcon.style.display = isPlaying ? 'block' : 'none';
  elements.readAloudBtnText.textContent = isPlaying ? 'ನಿಲ್ಲಿಸಿ (Stop)' : 'ಓದಿ ಕೇಳಿ (Read Aloud)';
}

function formatTime(secs) {
  const m = Math.floor(secs / 60);
  const s = Math.floor(secs % 60);
  return `${m}:${s < 10 ? '0' : ''}${s}`;
}

// ==============================================================================
// 9. Export & Print PDF
// ==============================================================================
function copyExtractedText() {
  const text = elements.kannadaEditor.value;
  if (!text) return;
  navigator.clipboard.writeText(text).then(() => {
    showToast('ಕನ್ನಡ ಪಠ್ಯ ನಕಲಿಸಲಾಗಿದೆ (Copied to clipboard)');
  });
}

function exportAsTxt() {
  const text = elements.kannadaEditor.value;
  if (!text) return;

  // UTF-8 BOM so Windows Notepad displays Kannada correctly
  const bom = new Uint8Array([0xEF, 0xBB, 0xBF]);
  const blob = new Blob([bom, text], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);

  const a = document.createElement('a');
  a.href = url;
  const baseName = (state.currentFileName || 'kannada_document').replace(/\.[^/.]+$/, '');
  a.download = `${baseName}_transcription.txt`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
  showToast('TXT ಕಡತ ಡೌನ್‌ಲೋಡ್ ಆಗಿದೆ (Downloaded TXT)');
}

function triggerPrintPdf() {
  // Populate print header
  const now = new Date();
  elements.printTimestamp.textContent = now.toLocaleString('en-IN', { timeZoneName: 'short' });
  elements.printMetaInfo.textContent = `ದಾಖಲೆಯ ಹೆಸರು / Document: ${state.currentFileName || 'Uploaded Kannada Document'} | ಪದಗಳು: ${elements.wordCountDisplay.textContent} | ಅಕ್ಷರಗಳು: ${elements.charCountDisplay.textContent}`;

  window.print();
}

// ==============================================================================
// 10. Zoom & Pan Controls
// ==============================================================================
function adjustZoom(delta) {
  setZoom(Math.min(Math.max(state.zoomLevel + delta, 0.5), 3.0));
}

function setZoom(level) {
  state.zoomLevel = level;
  elements.previewImage.style.transform = `scale(${level})`;
  elements.zoomLevelDisplay.textContent = `${Math.round(level * 100)}%`;
}

// ==============================================================================
// 11. Loading States & Dedicated 429/Error Banners
// ==============================================================================
function showOcrLoading(title, subtitle) {
  elements.loadingStepTitle.textContent = title;
  elements.loadingStepSub.textContent = subtitle;
  elements.ocrLoadingOverlay.style.display = 'flex';
}

function hideOcrLoading() {
  elements.ocrLoadingOverlay.style.display = 'none';
}

function showRateLimitError(msg, seconds = 5) {
  elements.rateLimitMsg.textContent = msg;
  elements.rateLimitBanner.style.display = 'flex';
  elements.generalErrorBanner.style.display = 'none';

  let countdown = seconds;
  elements.retryCountdown.textContent = `(Auto-retry in ${countdown}s...)`;

  clearInterval(state.retryTimer);
  state.retryTimer = setInterval(() => {
    countdown--;
    if (countdown > 0) {
      elements.retryCountdown.textContent = `(Auto-retry in ${countdown}s...)`;
    } else {
      clearInterval(state.retryTimer);
      elements.retryCountdown.textContent = '';
      executeRetry();
    }
  }, 1000);
}

function showGeneralError(title, msg) {
  elements.generalErrorTitle.textContent = `${title}:`;
  elements.generalErrorMsg.textContent = msg;
  elements.generalErrorBanner.style.display = 'flex';
  elements.rateLimitBanner.style.display = 'none';
}

function dismissErrors() {
  clearInterval(state.retryTimer);
  elements.rateLimitBanner.style.display = 'none';
  elements.generalErrorBanner.style.display = 'none';
  elements.scriptWarningBanner.style.display = 'none';
}

function executeRetry() {
  dismissErrors();
  if (typeof state.lastAction === 'function') {
    state.lastAction();
  }
}

// ==============================================================================
// 12. Toast Feedback
// ==============================================================================
let toastTimeout;
function showToast(message) {
  elements.toastMessage.textContent = message;
  elements.toastNotification.classList.add('show');
  clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => {
    elements.toastNotification.classList.remove('show');
  }, 2800);
}

// Start Application
document.addEventListener('DOMContentLoaded', initApp);
