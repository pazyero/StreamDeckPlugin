const list = document.getElementById("appList");
const excludedList = document.getElementById("excludedList");
const refreshBtn = document.getElementById("refresh");

async function loadApps() {
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

refreshBtn.onclick = loadApps;

// Auto-refresh every 3 seconds
setInterval(() => { loadApps(); loadExcluded(); }, 3000);
loadApps();
loadExcluded();

list.onclick = async (e) => {
  if (e.target.tagName === "BUTTON") {
    const name = e.target.dataset.name;
    await fetch(`http://127.0.0.1:8823/exclude?name=${name}`);
    await loadApps();
    await loadExcluded();
  }
};

excludedList.onclick = async (e) => {
  if (e.target.tagName === "BUTTON") {
    const name = e.target.dataset.name;
    await fetch(`http://127.0.0.1:8823/unexclude?name=${name}`);
    await loadExcluded();
    await loadApps();
  }
};
