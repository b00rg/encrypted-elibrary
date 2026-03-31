import { api } from './api.js';
import { state } from './state.js';

export async function loadShelfBooks() {
  const { ok, data } = await api('/shelf');
  if (!ok) return;

  const withDetails = await Promise.all(
    (data.books || []).map(async b => {
      if (!b.work_id) return { ...b, title: '[Encrypted]', author: '', description: '' };
      const { ok: dok, data: detail } = await api('/shelf/book/' + encodeURIComponent(b.work_id));
      return dok ? { ...b, ...detail } : { ...b, title: b.work_id, description: '' };
    })
  );
  state.shelfBooks = withDetails.reverse(); // newest first
}

export async function loadAdminUsers() {
  const { ok, data } = await api('/admin');
  if (ok) state.adminUsers = data.users || [];
}

export async function loadMyShelves() {
  const { ok, data } = await api('/shelves');
  if (ok) state.myShelves = data.shelves || [];
}

export async function loadActiveShelfBooks() {
  if (!state.activeShelfId) return;
  const { ok, data } = await api(`/shelves/${state.activeShelfId}/books`);
  if (!ok) { state.loadingShelfBooks = false; return; }

  const withDetails = await Promise.all(
    (data.books || []).map(async b => {
      if (!b.work_id) return { ...b, title: '[Encrypted]', author: '', description: '' };
      const { ok: dok, data: detail } = await api('/shelf/book/' + encodeURIComponent(b.work_id));
      return dok ? { ...b, ...detail } : { ...b, title: b.work_id, description: '' };
    })
  );
  state.activeShelfBooks = withDetails;
  state.loadingShelfBooks = false;
}

export async function loadAllBooksReviews() {
  const workIds = state.shelfBooks.filter(b => b.work_id).map(b => b.work_id);
  if (workIds.length === 0) return;
  await loadReadLaterReviews(workIds);
}

export async function loadReadLaterReviews(workIds) {
  const results = {};
  await Promise.all(
    workIds.map(async wid => {
      const { ok, data } = await api(`/reviews/for-work?work_id=${encodeURIComponent(wid)}`);
      if (ok) results[wid] = data.results || [];
    })
  );
  state.readLaterReviews = results;
}
