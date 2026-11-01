// HyperX SoloCastの接続状態とミュート状態をStream Deckへ反映するプラグイン。
let websocket = null;
let pluginUUID = null;
const contexts = new Map();
const displayedStates = new Map();
const API_BASE = "http://127.0.0.1:8823";
let statusEventSource = null;

function connectElgatoStreamDeckSocket(inPort, inUUID, inRegisterEvent, inInfo) {
  // Stream Deck本体とのWebSocket接続を確立するエントリーポイント。
  pluginUUID = inUUID;
  websocket = new WebSocket("ws://127.0.0.1:" + inPort);

  websocket.onopen = function () {
    // プラグイン登録後に、サーバーからの状態更新購読を開始する。
    websocket.send(JSON.stringify({
      event: inRegisterEvent,
      uuid: inUUID
    }));

    connectStatusEvents();
  };

  websocket.onmessage = function (event) {
    // 表示・設定・キー操作・非表示イベントをコンテキストごとに処理する。
    let message;
    try {
      message = JSON.parse(event.data);
    } catch (error) {
      return;
    }

    if (message.event === "willAppear" || message.event === "didReceiveSettings") {
      const context = message.context;
      contexts.set(context, message.payload && message.payload.settings
        ? message.payload.settings
        : contexts.get(context) || {});
    } else if (message.event === "keyDown") {
      toggleMute(message.context);
    } else if (message.event === "willDisappear") {
      contexts.delete(message.context);
    }
  };

  websocket.onclose = function () {
    disconnectStatusEvents();
  };
}

function connectStatusEvents() {
  // SSEからミュート状態を受け取り、すべての表示中ボタンへ反映する。
  disconnectStatusEvents();
  statusEventSource = new EventSource(API_BASE + "/miccontroller/events");

  statusEventSource.onmessage = function (event) {
    try {
      const status = JSON.parse(event.data);
      renderMuteState(
        Boolean(status.muted),
        status.connected === false
      );
    } catch (_) {}
  };

  statusEventSource.onerror = function () {
    // EventSource reconnects automatically. Keep the last confirmed state.
  };
}

function disconnectStatusEvents() {
  if (statusEventSource) {
    statusEventSource.close();
    statusEventSource = null;
  }
}

async function refreshStatus() {
  // SSEが利用できない場合に備え、RESTで現在状態を再取得する。
  try {
    const response = await fetch(
      API_BASE + "/miccontroller/status?_=" + Date.now(),
      { cache: "no-store" }
    );
    if (!response.ok) throw new Error("status request failed");
    const status = await response.json();
    renderMuteState(Boolean(status.muted), status.connected === false);
  } catch (_) {
    setDisconnectedState();
  }
}

async function toggleMute(context) {
  // ボタン押下時は即座に見た目を反転し、その後サーバーの実際の状態で補正する。
  const currentMuted = displayedStates.get(context) === true;
  const desiredMuted = !currentMuted;
  displayedStates.set(context, desiredMuted);
  sendToContext(context, contexts.get(context) || {}, desiredMuted, false);

  try {
    const response = await fetch(
      API_BASE + "/miccontroller/toggle?_=" + Date.now(),
      { cache: "no-store" }
    );
    if (!response.ok) {
      throw new Error("toggle request failed");
    }
    const result = await response.json();
    if (result.ok) {
      sendToContext(context, contexts.get(context) || {}, Boolean(result.muted), false);
    }
  } catch (_) {
    refreshStatus();
  }
}

function sendToContext(context, settings, muted, disconnected) {
  if (!websocket || websocket.readyState !== WebSocket.OPEN) return;
  displayedStates.set(context, muted);

  websocket.send(JSON.stringify({
    event: "setState",
    context: context,
    payload: { state: muted ? 0 : 1 }
  }));
}

function renderMuteState(muted, disconnected) {
  if (contexts.size === 0) return;
  contexts.forEach(function (settings, context) {
    sendToContext(context, settings, muted, disconnected);
  });
}

function setDisconnectedState() {
  renderMuteState(false, true);
}
