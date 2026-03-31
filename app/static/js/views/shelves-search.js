import { Icons } from '../icons.js';
import { escHtml } from '../utils.js';
import { state } from '../state.js';
import { api } from '../api.js';
import { showToast } from '../toast.js';
import { loadActiveShelfBooks } from '../data.js';
import { refreshPageBody } from '../app.js';

export async function doGroupSearch(q, rebind) {
  const resultsEl = document.getElementById('group-search-results');
  if (!resultsEl) return;
  resultsEl.innerHTML = `<div class="group-search-loading"><div class="spinner spinner-dark"></div></div>`;

  const { ok, data } = await api(`/shelf/search?q=${encodeURIComponent(q)}`);
  if (!ok || !data.results?.length) {
    resultsEl.innerHTML = `<p class="group-search-empty">No results found.</p>`;
    return;
  }

  resultsEl.innerHTML = `<div class="group-search-list">
    ${data.results.map(r => `
      <div class="group-search-item">
        ${r.cover_id
          ? `<img class="group-search-cover"
               src="https://covers.openlibrary.org/b/id/${escHtml(String(r.cover_id))}-S.jpg"
               onerror="this.style.display='none'" alt="${escHtml(r.title)}" />`
          : `<div class="group-search-cover group-search-cover-placeholder">${Icons.book}</div>`}
        <div class="group-search-info">
          <div class="group-search-title">${escHtml(r.title)}</div>
          <div class="group-search-author">${escHtml(r.author || '')}</div>
        </div>
        <button class="btn btn-primary btn-sm group-add-book-btn" style="width:auto"
          data-work-id="${escHtml(r.work_id)}" data-title="${escHtml(r.title)}">
          ${Icons.plus} Add
        </button>
      </div>`).join('')}
  </div>`;

  resultsEl.querySelectorAll('.group-add-book-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const workId = btn.dataset.workId;
      const title  = btn.dataset.title;
      btn.disabled = true;
      btn.innerHTML = `<div class="spinner"></div>`;

      const { ok, data } = await api(`/shelves/${state.activeShelfId}/books`, {
        method: 'POST',
        body: JSON.stringify({ work_id: workId }),
      });

      if (ok) {
        showToast(`"${title}" added to shelf!`, 'success');
        document.getElementById('group-search-input').value = '';
        document.getElementById('group-search-results').innerHTML = '';
        state.loadingShelfBooks = true;
        refreshPageBody();
        await loadActiveShelfBooks();
        refreshPageBody();
        if (rebind) rebind();
      } else {
        showToast(data.error || 'Failed to add book', 'error');
        btn.disabled = false;
        btn.innerHTML = `${Icons.plus} Add`;
      }
    });
  });
}
