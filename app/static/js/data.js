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
