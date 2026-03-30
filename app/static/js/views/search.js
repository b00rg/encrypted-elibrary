import { Icons } from '../icons.js';
import { escHtml, coverUrl, renderCoverImg } from '../utils.js';
import { state } from '../state.js';
import { api } from '../api.js';
import { getReadLater, toggleReadLater, isReadLater } from '../readLater.js';
import { showToast } from '../toast.js';
import { loadShelfBooks } from '../data.js';
import { openBookModal } from './modal.js';
// refreshPageBody is imported from app.js.
// The circular reference is safe: only called inside async functions/event handlers.
import { refreshPageBody } from '../app.js';

export function renderSearchResults() {
  const results = state.searchResults;
  return `
  <div class="search-section">
    <div class="search-section-header">
      <div class="search-section-title">
        Results for &ldquo;${escHtml(state.searchQuery)}&rdquo;
        ${!state.searchLoading ? `<span class="count-badge" style="margin-left:8px">${results.length}</span>` : ''}
      </div>
      <button class="search-clear" id="search-clear-btn">Clear search</button>
    </div>
    ${state.searchLoading
      ? `<div style="display:flex;align-items:center;gap:10px;padding:8px 0;color:var(--text-muted);font-size:0.875rem">
           <div class="spinner spinner-dark"></div> Searching…
         </div>`
      : results.length === 0
        ? `<p style="color:var(--text-muted);font-size:0.875rem">No results found. Try a different search.</p>`
        : `<div class="book-grid">${results.map(renderSearchCard).join('')}</div>`}
  </div>`;
}

function renderSearchCard(book) {
  const url = coverUrl(book.cover_id);
  const saved = isReadLater(book.work_id);
  return `
  <div class="book-card" data-work-id="${escHtml(book.work_id)}"
       data-title="${escHtml(book.title)}" data-author="${escHtml(book.author || '')}"
       data-cover="${escHtml(url || '')}" data-year="${escHtml(String(book.year || ''))}">
    ${saved ? `<div class="rl-badge" title="Saved to Read Later">${Icons.bookmarkFill}</div>` : ''}
    ${renderCoverImg(url, book.title)}
    <div class="book-info">
      <div class="book-title">${escHtml(book.title)}</div>
      ${book.author ? `<div class="book-author">${escHtml(book.author)}</div>` : ''}
      <div class="book-meta">
        ${book.year ? `<span class="book-year">${escHtml(String(book.year))}</span>` : '<span></span>'}
      </div>
    </div>
    <div class="card-actions">
      <button class="btn btn-primary btn-sm search-add-btn" data-work-id="${escHtml(book.work_id)}"
              data-title="${escHtml(book.title)}">
        ${Icons.plus} Add
      </button>
      <button class="btn ${saved ? 'btn-rl-saved' : 'btn-outline'} btn-sm rl-btn"
              data-work-id="${escHtml(book.work_id)}"
              title="${saved ? 'Remove from Read Later' : 'Save to Read Later'}">
        ${saved ? Icons.bookmarkFill : Icons.bookmark}
      </button>
    </div>
  </div>`;
}

export async function doSearch(query) {
  if (!query) { clearSearch(); return; }
  state.searchQuery = query;
  state.searchResults = [];
  state.searchLoading = true;
  refreshPageBody();

  const { ok, data } = await api('/shelf/search?q=' + encodeURIComponent(query));
  state.searchLoading = false;
  if (ok) state.searchResults = data.results || [];
  refreshPageBody();
  if (ok) bindSearchResultEvents();
}

export function clearSearch() {
  state.searchQuery = '';
  state.searchResults = [];
  state.searchLoading = false;
  const input = document.getElementById('search-input');
  if (input) input.value = '';
  refreshPageBody();
}

export function bindSearchResultEvents() {
  document.getElementById('search-clear-btn')?.addEventListener('click', () => {
    clearSearch();
    const input = document.getElementById('search-input');
    if (input) input.value = '';
  });

  document.querySelectorAll('.search-add-btn').forEach(btn => {
    btn.addEventListener('click', async e => {
      e.stopPropagation();
      const workId = btn.dataset.workId;
      const title  = btn.dataset.title;
      const orig   = btn.innerHTML;
      btn.disabled = true;
      btn.innerHTML = `<div class="spinner"></div>`;

      const { ok, data } = await api('/shelf/add', {
        method: 'POST', body: JSON.stringify({ work_id: workId }),
      });
      if (ok) {
        showToast(`"${title}" added to the shelf!`, 'success');
        btn.innerHTML = `${Icons.check} Added`;
        btn.classList.remove('btn-primary');
        btn.classList.add('btn-outline');
        await loadShelfBooks();
      } else {
        showToast(data.error || 'Failed to add book.', 'error');
        btn.disabled = false;
        btn.innerHTML = orig;
      }
    });
  });

  document.querySelectorAll('.search-section .rl-btn').forEach(btn => {
    btn.addEventListener('click', e => {
      e.stopPropagation();
      const workId = btn.dataset.workId;
      const nowSaved = toggleReadLater(workId);
      showToast(nowSaved ? 'Added to Read Later.' : 'Removed from Read Later.', 'success');
      btn.innerHTML = nowSaved ? Icons.bookmarkFill : Icons.bookmark;
      btn.className = `btn ${nowSaved ? 'btn-rl-saved' : 'btn-outline'} btn-sm rl-btn`;
      btn.title = nowSaved ? 'Remove from Read Later' : 'Save to Read Later';
      const card = btn.closest('.book-card');
      const badge = card?.querySelector('.rl-badge');
      if (nowSaved && !badge) {
        card.insertAdjacentHTML('afterbegin', `<div class="rl-badge">${Icons.bookmarkFill}</div>`);
      } else if (!nowSaved && badge) {
        badge.remove();
      }
    });
  });

  document.querySelectorAll('.search-section .book-card').forEach(card => {
    card.addEventListener('click', e => {
      if (e.target.closest('.search-add-btn') || e.target.closest('.rl-btn')) return;
      openBookModal({
        work_id: card.dataset.workId,
        title:   card.dataset.title,
        author:  card.dataset.author,
        cover:   card.dataset.cover,
        year:    card.dataset.year,
      });
    });
  });
}
