// Property Inspector: サーバーへ問い合わせるアプリ一覧と除外設定を表示する。
const list = document.getElementById("appList");
const excludedList = document.getElementById("excludedList");
const refreshBtn = document.getElementById("refresh");

async function loadApps() {
  // 現在の音量セッション一覧を取得し、除外ボタン付きで再描画する。
  try {
    const r = await fetch("http://127.0.0.1:8823/apps");
    const apps = await r.json();
    list.innerHTML = "";
    for (const a of apps) {
      const li = document.createElement("li");
      const volume = Math.round(a.volume * 100);
      li.innerHTML = `${a.name} - <span id="vol-${a.name}">` +  volume + '%' + `</span> <button data-name="${a.name}">Exclude</button>`;
      list.appendChild(li);
    }
  } catch (e) {
    console.error('loadApps error', e);
    list.innerHTML = '<li>Error loading apps</li>';
  }
}

async function loadExcluded() {
  // 除外済みアプリ一覧を取得し、解除ボタン付きで再描画する。
  try {
    const r = await fetch("http://127.0.0.1:8823/excluded");
    const items = await r.json();
    excludedList.innerHTML = "";
    for (const name of items) {
      const li = document.createElement("li");
      li.innerHTML = `${name} <button data-name="${name}">Unexclude</button>`;
      excludedList.appendChild(li);
    }
  } catch (e) {
    console.error('loadExcluded error', e);
    excludedList.innerHTML = '<li>Error loading excluded list</li>';
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
    await fetch(`http://127.0.0.1:8823/exclude?name=${name}`);
    await loadApps();
    await loadExcluded();
  }
};

excludedList.onclick = async (e) => {
  // 除外解除ボタンで指定アプリを解除し、両方の一覧へ変更を反映する。
  if (e.target.tagName === "BUTTON") {
    const name = e.target.dataset.name;
    await fetch(`http://127.0.0.1:8823/unexclude?name=${name}`);
    await loadExcluded();
    await loadApps();
  }
};
