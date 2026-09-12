const KEY = "onimusha-save-viewer:current";

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
