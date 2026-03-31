import { Icons } from '../icons.js';
import { escHtml, renderColorCover, SHELF_COLORS, SHARED_SHELF_COLOR } from '../utils.js';
import { state } from '../state.js';
import { getReadLater, isReadLater } from '../readLater.js';
import { renderSearchResults } from './search.js';

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
      ${state.myShelves.length > 0 ? `
        <span class="filter-tab-divider"></span>
        ${state.myShelves.map((s, i) => {
          const c = SHELF_COLORS[i % SHELF_COLORS.length];
          return `<button class="filter-tab shelf-nav-tab" data-shelf-nav-id="${s.id}">
            <span class="shelf-color-dot" style="background:${c}"></span>${escHtml(s.name)}
          </button>`;
        }).join('')}` : ''}
    </div>

    <div class="rl-controls">
      <p class="rl-controls-hint">
        ${Icons.info} Reviews from your shelves are shown below each book.
        Non-members only see the encrypted ciphertext.
      </p>
      <button class="btn btn-outline btn-sm" id="toggle-enc-global">
        ${state.showEncryptedReviews ? '🔓 Show Decrypted' : '🔒 Show Encrypted'}
      </button>
    </div>

    <div class="rl-book-list" id="shelf-grid">
      ${state.loadingShelf
        ? renderSkeletonRows(4)
        : books.length === 0
          ? renderShelfEmpty()
          : books.map(renderShelfRow).join('')}
    </div>
  </div>`;
}

function renderSkeletonRows(n = 4) {
  return Array.from({ length: n }, () => `
    <div class="rl-book-row skeleton-card" style="display:flex;gap:16px;padding:16px">
      <div class="skeleton" style="width:80px;height:120px;border-radius:6px;flex-shrink:0"></div>
      <div style="flex:1;display:flex;flex-direction:column;gap:8px">
        <div class="skeleton skeleton-line" style="width:80%"></div>
        <div class="skeleton skeleton-line" style="width:50%"></div>
        <div class="skeleton skeleton-line-short"></div>
      </div>
    </div>`).join('');
}

export function renderShelfEmpty() {
  return state.readLaterFilter
    ? `<div class="empty-state">
        <div class="empty-state-icon">${Icons.bookmark}</div>
        <h3>Nothing saved yet</h3>
        <p>Click the bookmark icon on any card to save it here.</p>
       </div>`
    : `<div class="empty-state">
        <div class="empty-state-icon">${Icons.book}</div>
        <h3>Your shelf is empty</h3>
        <p>Search for a book above and add it to the shared shelf.</p>
       </div>`;
}

export function renderShelfRow(book) {
  const saved = book.work_id && isReadLater(book.work_id);
  const canDelete = book.added_by === state.user?.username || state.user?.is_admin;

  return `
  <div class="rl-book-row">
    <div class="rl-book-header">
      <div class="rl-cover-wrap">
        ${renderColorCover(book.title || 'Unknown', SHARED_SHELF_COLOR, 'rl-cover')}
      </div>
      <div class="rl-book-info">
        <div class="book-title">${escHtml(book.title || 'Unknown Title')}</div>
        ${book.author ? `<div class="book-author">${escHtml(book.author)}</div>` : ''}
        ${book.year ? `<div class="book-year" style="display:inline-block;margin-top:4px">${escHtml(String(book.year))}</div>` : ''}
        <div class="book-added-by" style="margin-top:6px">
          ${Icons.user} Added by ${escHtml(book.added_by || '?')}
        </div>
      </div>
      <div class="rl-row-actions">
        <button class="btn ${saved ? 'btn-rl-saved' : 'btn-outline'} btn-sm rl-btn"
          data-work-id="${escHtml(book.work_id || '')}"
          title="${saved ? 'Remove from Read Later' : 'Save to Read Later'}">
          ${saved ? Icons.bookmarkFill : Icons.bookmark} ${saved ? 'Saved' : 'Read Later'}
        </button>
        <button class="btn btn-outline btn-sm shelf-card-go-link"
          data-work-id="${escHtml(book.work_id || '')}"
          title="Open on OpenLibrary">
          ${Icons.external} Link
        </button>
        ${canDelete ? `
        <button class="btn btn-danger btn-sm shared-delete-btn"
          data-book-id="${book.id}"
          data-title="${escHtml(book.title || '')}">
          ${Icons.trash} Delete
        </button>` : ''}
      </div>
    </div>

    <div class="rl-reviews-section">
      ${renderInlineReviews(book.work_id)}
    </div>
  </div>`;
}

function renderInlineReviews(workId) {
  if (!workId) {
    return `<div class="rl-reviews-empty">Book ID is encrypted — join the shelf to decrypt.</div>`;
  }

  if (state.loadingReadLaterReviews) {
    return `<div class="rl-reviews-loading">
      <div class="spinner spinner-dark"></div> Loading reviews…
    </div>`;
  }

  const groups = state.readLaterReviews[workId];
  if (!groups) {
    return `<div class="rl-reviews-empty">No review data loaded yet.</div>`;
  }
  if (groups.length === 0) {
    return `<div class="rl-reviews-empty">No reviews from your shelves for this book.</div>`;
  }

  return groups.map(group => {
    const shelfIdx = state.myShelves.findIndex(s => s.id === group.shelf_id);
    const color = shelfIdx >= 0 ? SHELF_COLORS[shelfIdx % SHELF_COLORS.length] : SHARED_SHELF_COLOR;
    return `
    <div class="rl-reviews-group">
      <div class="rl-reviews-shelf-name" style="color:${color}">
        <span class="shelf-color-dot" style="background:${color}"></span>
        ${Icons.shelf} ${escHtml(group.shelf_name)}
      </div>
      ${group.reviews.length === 0
        ? `<div class="rl-reviews-empty" style="padding:4px 0">No reviews yet on this shelf.</div>`
        : group.reviews.map(r => `
          <div class="review-card">
            <div class="review-header">
              <span class="review-author">${Icons.user} ${escHtml(r.reviewer_username)}</span>
              <span class="review-date">${escHtml(r.created_at)}</span>
            </div>
            <div class="review-text${state.showEncryptedReviews ? ' hidden' : ''}">
              ${escHtml(r.review || '[Could not decrypt]')}
            </div>
            <div class="review-enc-text${state.showEncryptedReviews ? '' : ' hidden'}">
              ${escHtml(r.review_enc)}
            </div>
          </div>`).join('')}
    </div>`;
  }).join('');
}
