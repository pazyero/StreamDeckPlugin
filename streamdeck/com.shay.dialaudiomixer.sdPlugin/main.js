// =======================
// DialAudioMixer main.js
// =======================

// WebSocket接続用
let websocket = null;
// プラグインUUID
let pluginUUID = null;
// アクションコンテキスト（各ボタン固有のUUID）
let actionContext = null;
// 現在表示中のタイトル
let title = "(No Audio Apps)";
// 設定保持用
let settings = {};
// 中断コントローラー（fetchタイムアウト用）
const timeoutId = setTimeout(() => controller.abort(), 500); // 500ms = 0.5秒

const muteOverlaySrc = "./images/mute_overlay.png"; // 144x144, 透明背景


// =======================
// Stream Deckとの接続
// =======================
function connectElgatoStreamDeckSocket(inPort, inUUID, inRegisterEvent, inInfo) {
  try {
    connectElgatoPlugin(inUUID, inRegisterEvent, { port: inPort }, inInfo);
  } catch (e) {
    console.error('connectElgatoStreamDeckSocket error', e);
  }
}

// =======================
// デバッグログ送信
// =======================
function sendDebug(msg) {
  try {
    fetch('http://127.0.0.1:8823/_log?m=' + encodeURIComponent(String(msg))).catch(() => {});
  } catch (e) {}
}

sendDebug('loaded render');

// =======================
// プラグイン接続・イベント処理
// =======================
function connectElgatoPlugin(inUUID, inMessage, inAppInfo, inActionInfo) {
  pluginUUID = inUUID;
  try {
    websocket = new WebSocket("ws://127.0.0.1:" + inAppInfo.port);
  } catch (e) {
    sendDebug('WebSocket error: ' + String(e));
    console.error('WebSocket create error', e, inAppInfo);
    return;
  }

  websocket.onopen = function () {
    const json = { event: inMessage, uuid: inUUID };
    try { websocket.send(JSON.stringify(json)); } catch (e) {}

    // アプリ情報取得開始
    fetchApps();

    // 定期的にアプリ情報と音量情報を取得
    if (window.__damp_pollInterval) clearInterval(window.__damp_pollInterval);
    window.__damp_pollInterval = setInterval(fetchApps, 2000);
  };

  websocket.onmessage = function (evt) {
    let msg = null;
    try { msg = JSON.parse(evt.data); } catch (e) { return; }

    const ev = msg.event;

    sendDebug(ev);

    // ボタン表示時のコンテキスト取得
    if (ev === "willAppear") {
      actionContext = msg.context;
      fetchApps();
    }

    // まだコンテキストが未設定の場合は捕捉
    if (!actionContext && msg.context) actionContext = msg.context;

    // 設定更新イベント
    if (ev === "didReceiveSettings" || ev === "appearance") {
      fetchApps();
    }

    // ダイヤル押下イベント
    if (ev === "dialDown") {
      rotateNextApp();
    }

    // ディスプレイ部分タッチイベント
    if (ev === "touchTap") {
      adjustMute();
    }


    // ダイヤル回転イベント
    let ticks = 0;
    if (msg.payload) {
      if (msg.payload.ticks !== undefined) ticks = msg.payload.ticks;
      else if (msg.payload.rotation !== undefined) ticks = msg.payload.rotation;
      else if (msg.payload.delta !== undefined) ticks = msg.payload.delta;
    }
    if (ticks !== 0) adjustVolume(ticks);
  };

  websocket.onclose = function () {
    if (window.__damp_pollInterval) {
      clearInterval(window.__damp_pollInterval);
      window.__damp_pollInterval = null;
    }
  };

  websocket.onerror = function (err) { console.debug('WebSocket error', err); };
}

// =======================
// アプリ情報管理
// =======================
let currentIndex = 1;
let apps = [];
// アプリ名称ごとのアイコンキャッシュ
const iconCache = {};

// アプリアイコン取得
async function fetchIconForApp(pid, name) {
  if (iconCache[name]){return iconCache[name];}
  try {
    const res = await fetch(`http://127.0.0.1:8823/icon?pid=${pid}`);
    if (!res.ok) throw new Error('no icon');
    const j = await res.json();
    if (j && j.data_url) {
      iconCache[name] = j.data_url;
      return j.data_url;
    }
  } catch (e) {
    sendDebug('fetchIconForApp error: ' + String(e));
  }
  return null;
}

// 現在選択中のアプリを取得
function getActiveApp() {
  if (apps.length === 0) return null;
  const idx = currentIndex - 1;
  if (idx < 0 || idx >= apps.length) return null;
  return apps[idx];
}

// 次のアプリに切り替え
function rotateNextApp() {
  if (apps.length === 0) { fetchApps(); return; }
  currentIndex = currentIndex + 1;
  if (currentIndex > apps.length) currentIndex = 1;
  sendDebug('rotateNextApp called, apps.length=' + apps.length + ', currentIndex=' + currentIndex);
  updateDialTitle();
  fetchApps();
}

// ダイヤルタイトル（アプリ名 + 音量）更新
async function updateDialTitle() {
  if (!websocket || websocket.readyState !== 1) return;

  const app = getActiveApp();
   if (!app) return;

  const volPercent = Math.round(app.volume * 100);
  const imgData = await renderImageForDial(app.name, volPercent, app.mute, iconCache[app.name] || null);

  const ctx = actionContext || pluginUUID;
  websocket.send(JSON.stringify({
    event: "setFeedback",
    context: ctx,
    payload: {
      title: app.name,
      value: volPercent + '%',
      indicator: { value: volPercent },
      icon: imgData
    }
  }));
}


// 音量表示更新
function updateVolumeDisplay() {
  volume = 0.0;
  const app = getActiveApp();
  if (app){
    title = app.name;
    volume = app.volume;
  }
  const dispEl = document.getElementById('display');
  if (dispEl && getActiveApp()) {
    const volPercent = Math.round(volume * 100);
    dispEl.textContent = getActiveApp().name + '\n' + volPercent + '%';
  }

  try {
    if (!app) return;
    const volPercent = Math.round(volume * 100);
    const ctx = actionContext || pluginUUID;

    const payload = {
      event: "setFeedback",
      context: ctx,
      payload: { title: title, value: volPercent+'%', indicator: { value: volPercent } } // 画像なしで送信
    };

    // デバッグログ
    websocket.send(JSON.stringify(payload));
  } catch (e) {
    sendDebug('updateVolumeDisplay image error: ' + String(e)); 
  }
}


// =======================
//  ミュート切替
// =======================
function adjustMute() {
  const app = getActiveApp();
  if (!app) return;

 sendDebug(app.mute);
  mute = ! app.mute;
  sendDebug('adjustVolume: local vol=' + app.volume.toFixed(2) + `, name=${app.name}&mute=${mute}`);

  app.mute = mute
  updateDialTitle();

  fetch(`http://127.0.0.1:8823/mute_set?name=${app.name}&mute=${mute}`).catch(() => {})
  .finally(() => clearTimeout(timeoutId));
}




// =======================
// 音量調整
// =======================
function adjustVolume(ticks) {
  const step = 0.03;
  const app = getActiveApp();
  if (!app) return;

  volume = Math.min(1.0, Math.max(0.0, app.volume + (ticks * step)));
  sendDebug('adjustVolume: local vol=' + app.volume.toFixed(2) + `, name=${app.name}&vol=${app.volume}`);

  app.volume= volume
  updateVolumeDisplay();

  fetch(`http://127.0.0.1:8823/volume_set?name=${app.name}&vol=${volume}`).catch(() => {})
  .finally(() => clearTimeout(timeoutId));;
}

// =======================
// アプリ一覧取得
// =======================
function fetchApps() {
  fetch('http://127.0.0.1:8823/apps')
    .then(res => res.json())
    .then(list => {
      if (!Array.isArray(list)) return;

      const prevLen = apps.length;
      apps = list.map(i => ({ pid: i.pid, mute:i.mute, name: i.name, volume: i.volume }));

      if (apps.length < prevLen) currentIndex = 1;
      if (currentIndex < 1 || currentIndex > apps.length) currentIndex = apps.length > 0 ? 1 : 0;

      // アイコン取得（非同期キャッシュ）
      apps.forEach(app => {
        fetchIconForApp(app.pid, app.name).then(icon => {
          const active = getActiveApp();
          if (active && active.pid === app.pid) {
            updateDialTitle();
          }
        });
      });

      updateDialTitle();
    })
    .catch(err => { sendDebug('fetchApps error: ' + String(err)); })
    .finally(() => clearTimeout(timeoutId));;
}

// =======================
// ダイヤル用画像生成（Base64 PNG）
// =======================
function renderImageForDial(title, volPercent, muted = false, iconSrc = null) {
  return new Promise((resolve) => {
    const size = 144;
    const canvas = document.createElement('canvas');
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext('2d');

    // 背景は透明
    ctx.clearRect(0, 0, size, size);

    const drawOverlay = () => {
      if (muted) {
        const overlay = new Image();
        overlay.src = muteOverlaySrc;
        overlay.onload = () => {
          ctx.drawImage(overlay, 0, 0, size, size);
          resolve(canvas.toDataURL('image/png'));
        };
        overlay.onerror = () => resolve(canvas.toDataURL('image/png'));
      } else {
        resolve(canvas.toDataURL('image/png'));
      }
    };

    if (iconSrc) {
      // アイコン描画
      const img = new Image();
      img.src = iconSrc;
      img.onload = () => {
        ctx.drawImage(img, 0, 0, size, size);
        drawOverlay();
      };
      img.onerror = () => {
        // アイコン読み込み失敗時は円表示
        drawCircleDisplay();
        drawOverlay();
      };
    } else {
      // アイコンなし → 円＋音量
      drawCircleDisplay();
      drawOverlay();
    }

    function drawCircleDisplay() {
      const cx = size / 2;
      const cy = size / 2 - 8;
      const radius = Math.min(size, size) * 0.35;

      // 外円
      ctx.beginPath();
      ctx.arc(cx, cy, radius + 8, 0, 2 * Math.PI);
      ctx.fillStyle = '#111';
      ctx.fill();

      // 内円
      ctx.beginPath();
      ctx.arc(cx, cy, radius, 0, 2 * Math.PI);
      ctx.fillStyle = '#222';
      ctx.fill();

      // 音量バー
      const start = -Math.PI / 2;
      const end = start + (volPercent / 100) * 2 * Math.PI;
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.arc(cx, cy, radius - 4, start, end);
      ctx.closePath();
      ctx.fillStyle = '#00cc88';
      ctx.fill();

      // 音量文字
      ctx.fillStyle = '#fff';
      ctx.font = Math.floor(size * 0.12) + 'px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(volPercent + '%', cx, cy + radius + 20);

      // アプリ名
      ctx.font = Math.floor(size * 0.09) + 'px sans-serif';
      const short = title.length > 16 ? title.slice(0, 13) + '...' : title;
      ctx.fillText(short, cx, size - 8);
    }
  });
}