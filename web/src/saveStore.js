const KEY = "onimusha-save-viewer:current";
const STEAM_KEY = "onimusha-save-viewer:steamid";

export function loadSteamId() {
  try {
    return (localStorage.getItem(STEAM_KEY) || "").trim();
  } catch {
    return "";
  }
}

export function saveSteamId(value) {
  const id = String(value || "").replace(/\s+/g, "").trim();
  if (!id) {
    localStorage.removeItem(STEAM_KEY);
    return;
  }
  localStorage.setItem(STEAM_KEY, id);
}

export async function loadLatestSave() {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    return parsed?.save ? parsed : null;
  } catch {
    return null;
  }
}

export async function saveLatestSave(record) {
  localStorage.setItem(KEY, JSON.stringify(record));
}
