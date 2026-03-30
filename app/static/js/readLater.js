const RL_KEY = 'bookshelf_read_later';

export function getReadLater() {
  try { return new Set(JSON.parse(localStorage.getItem(RL_KEY) || '[]')); }
  catch { return new Set(); }
}

export function toggleReadLater(workId) {
  const set = getReadLater();
  if (set.has(workId)) { set.delete(workId); } else { set.add(workId); }
  localStorage.setItem(RL_KEY, JSON.stringify([...set]));
  return set.has(workId);
}

export function isReadLater(workId) {
  return getReadLater().has(workId);
}
