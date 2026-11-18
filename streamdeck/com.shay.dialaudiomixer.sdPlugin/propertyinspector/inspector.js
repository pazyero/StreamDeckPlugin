// Property Inspector: サーバーへ問い合わせるアプリ一覧と除外設定を表示する。
const list = document.getElementById("appList");
const excludedList = document.getElementById("excludedList");
const refreshBtn = document.getElementById("refresh");
const API_BASE = "http://127.0.0.1:8823";

async function loadApps() {
  // 現在の音量セッション一覧を取得し、除外ボタン付きで再描画する。
  try {
    const r = await fetch(API_BASE + "/dialAudioMixer/apps");
    const apps = await r.json();
    list.textContent = "";
    for (const a of apps) {
      const li = document.createElement("li");
      const volume = Math.round(a.volume * 100);
      const button = document.createElement("button");
      button.textContent = "Exclude";
      button.dataset.name = a.name;
      li.appendChild(document.createTextNode(`${a.name} - `));
      li.appendChild(document.createTextNode(volume + "% "));
      li.appendChild(button);
      list.appendChild(li);
    }
  } catch (e) {
    console.error('loadApps error', e);
    list.textContent = "";
    const li = document.createElement("li");
    li.textContent = "Error loading apps";
    list.appendChild(li);
  }
}

async function loadExcluded() {
  // 除外済みアプリ一覧を取得し、解除ボタン付きで再描画する。
  try {
    const r = await fetch(API_BASE + "/dialAudioMixer/excluded");
    const items = await r.json();
    excludedList.textContent = "";
    for (const name of items) {
      const li = document.createElement("li");
      const button = document.createElement("button");
      button.textContent = "Unexclude";
      button.dataset.name = name;
      li.appendChild(document.createTextNode(`${name} `));
      li.appendChild(button);
      excludedList.appendChild(li);
    }
  } catch (e) {
    console.error('loadExcluded error', e);
    excludedList.textContent = "";
    const li = document.createElement("li");
    li.textContent = "Error loading excluded list";
    excludedList.appendChild(li);
  }
}

// 手動更新と初回/定期更新で同じ一覧更新処理を再利用する。
refreshBtn.onclick = loadApps;

// Auto-refresh every 3 seconds
setInterval(() => { loadApps(); loadExcluded(); }, 3000);
loadApps();
loadExcluded();

list.onclick = async (e) => {
  // 表示中アプリの除外ボタンからアプリ名を取得し、一覧へ反映する。
  if (e.target.tagName === "BUTTON") {
    const name = e.target.dataset.name;
    await fetch(API_BASE + "/dialAudioMixer/exclude?name=" + encodeURIComponent(name));
    await loadApps();
    await loadExcluded();
  }
};

excludedList.onclick = async (e) => {
  // 除外解除ボタンで指定アプリを解除し、両方の一覧へ変更を反映する。
  if (e.target.tagName === "BUTTON") {
    const name = e.target.dataset.name;
    await fetch(API_BASE + "/dialAudioMixer/unexclude?name=" + encodeURIComponent(name));
    await loadExcluded();
    await loadApps();
  }
};
