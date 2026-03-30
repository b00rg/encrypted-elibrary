import { Icons } from '../icons.js';
import { escHtml, coverUrl, workCoverUrl, renderCoverImg } from '../utils.js';
import { state } from '../state.js';
import { getReadLater, toggleReadLater, isReadLater } from '../readLater.js';
import { showToast } from '../toast.js';
import { openBookModal } from './modal.js';
import { renderSearchResults, bindSearchResultEvents } from './search.js';
// refreshPageBody is imported from app.js.
// The circular reference is safe: only called inside event handlers.
import { refreshPageBody } from '../app.js';

export function renderShelfPage() {
  const hasSearch = state.searchQuery && state.searchResults.length >= 0;
  const allBooks = state.shelfBooks;
  const rlSet = getReadLater();
  const rlCount = allBooks.filter(b => b.work_id && rlSet.has(b.work_id)).length;
  const books = state.readLaterFilter
    ? allBooks.filter(b => b.work_id && rlSet.has(b.work_id))
    : allBooks;

  return `
  <div>
    ${hasSearch ? renderSearchResults() : ''}

    <div class="section-header">
      <div>
        <h1 class="section-title">Our Shared Shelf</h1>
        <p class="section-subtitle">Books encrypted and shared with all members.</p>
      </div>
      ${!state.loadingShelf ? `<span class="count-badge">${allBooks.length} book${allBooks.length !== 1 ? 's' : ''}</span>` : ''}
    </div>

    <div class="shelf-filter-tabs">
      <button class="filter-tab ${!state.readLaterFilter ? 'active' : ''}" id="filter-all">
        ${Icons.shelf} All Books
      </button>
      <button class="filter-tab ${state.readLaterFilter ? 'active' : ''}" id="filter-rl">
        ${Icons.bookmark} Read Later${rlCount > 0 ? ` <span class="filter-count">${rlCount}</span>` : ''}
      </button>
    </div>

    <div class="book-grid" id="shelf-grid">
      ${state.loadingShelf
        ? renderSkeletonCards(8)
        : books.length === 0
          ? renderShelfEmpty()
          : books.map(renderShelfCard).join('')}
    </div>
  </div>`;
}

function renderSkeletonCards(n = 8) {
  return Array.from({ length: n }, () => `
    <div class="skeleton-card">
      <div class="skeleton skeleton-cover"></div>
      <div class="skeleton-body">
        <div class="skeleton skeleton-line" style="width:90%"></div>
        <div class="skeleton skeleton-line" style="width:70%"></div>
        <div class="skeleton skeleton-line-short"></div>
      </div>
    </div>`).join('');
}

export function renderShelfEmpty() {
  return state.readLaterFilter
    ? `<div class="empty-state" style="grid-column:1/-1">
        <div class="empty-state-icon">${Icons.bookmark}</div>
        <h3>Nothing saved yet</h3>
        <p>Click the bookmark icon on any card to save it here.</p>
       </div>`
    : `<div class="empty-state" style="grid-column:1/-1">
        <div class="empty-state-icon">${Icons.book}</div>
        <h3>Your shelf is empty</h3>
        <p>Search for a book above and add it to the shared shelf.</p>
       </div>`;
}

export function renderShelfCard(book) {
  const url = book.cover_id ? coverUrl(book.cover_id) : workCoverUrl(book.work_id);
  const saved = book.work_id && isReadLater(book.work_id);
  return `
  <div class="book-card" data-work-id="${escHtml(book.work_id)}"
       data-title="${escHtml(book.title)}" data-author="${escHtml(book.author || '')}"
       data-cover="${escHtml(url)}" data-desc="${escHtml(book.description || '')}"
       data-year="${escHtml(String(book.year || ''))}" data-added="${escHtml(book.added_by || '')}">
    ${saved ? `<div class="rl-badge" title="Saved to Read Later">${Icons.bookmarkFill}</div>` : ''}
    ${renderCoverImg(url, book.title)}
    <div class="book-info">
      <div class="book-title">${escHtml(book.title || 'Unknown Title')}</div>
      ${book.author ? `<div class="book-author">${escHtml(book.author)}</div>` : ''}
      ${book.description
        ? `<div class="book-desc">${escHtml(book.description)}</div>`
        : `<div class="book-desc" style="opacity:0.4;font-style:italic">No description available.</div>`}
      <div class="book-meta">
        <div class="book-added-by">
          ${Icons.user} Added by <strong style="margin-left:3px">${escHtml(book.added_by || '?')}</strong>
        </div>
        ${book.year ? `<span class="book-year">${escHtml(String(book.year))}</span>` : ''}
      </div>
    </div>
    <div class="card-actions">
      <button class="btn ${saved ? 'btn-rl-saved' : 'btn-outline'} btn-sm rl-btn"
              data-work-id="${escHtml(book.work_id)}"
              title="${saved ? 'Remove from Read Later' : 'Save to Read Later'}">
        ${saved ? Icons.bookmarkFill : Icons.bookmark} ${saved ? 'Saved' : 'Read Later'}
      </button>
      <button class="btn btn-outline btn-sm shelf-card-details" data-work-id="${escHtml(book.work_id)}"
              title="View details">
        ${Icons.external}
      </button>
    </div>
  </div>`;
}

export function bindShelfEvents() {
  document.getElementById('filter-all')?.addEventListener('click', () => {
    state.readLaterFilter = false;
    refreshPageBody();
  });
  document.getElementById('filter-rl')?.addEventListener('click', () => {
    state.readLaterFilter = true;
    refreshPageBody();
  });

  const grid = document.getElementById('shelf-grid');
  if (!grid) return;

  grid.addEventListener('click', e => {
    const rlBtn = e.target.closest('.rl-btn');
    if (rlBtn) {
      e.stopPropagation();
      const workId = rlBtn.dataset.workId;
      const nowSaved = toggleReadLater(workId);
      showToast(nowSaved ? 'Added to Read Later.' : 'Removed from Read Later.', 'success');
      refreshPageBody();
      if (state.searchQuery) bindSearchResultEvents();
      return;
    }

    const card = e.target.closest('.book-card');
    const detailsBtn = e.target.closest('.shelf-card-details');

    if (detailsBtn || card) {
      const c = card || detailsBtn.closest('.book-card');
      if (c) openBookModal({
        work_id:     c.dataset.workId,
        title:       c.dataset.title,
        author:      c.dataset.author,
        cover:       c.dataset.cover,
        description: c.dataset.desc,
        year:        c.dataset.year,
        added_by:    c.dataset.added,
        fromShelf:   true,
      });
    }
  });
}
