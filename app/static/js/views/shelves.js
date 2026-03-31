import { Icons } from '../icons.js';
import { escHtml, coverUrl, workCoverUrl, renderCoverImg, openLibraryUrl, SHELF_COLORS } from '../utils.js';
import { state } from '../state.js';
import { isReadLater } from '../readLater.js';

// ── Page render ───────────────────────────────────────────────────────

export function renderShelvesPage() {
  const shelves = state.myShelves;

  return `
  <div>
    <div class="section-header">
      <div>
        <h1 class="section-title">My Shelves</h1>
        <p class="section-subtitle">Private reading groups with encrypted books and reviews.</p>
      </div>
      <button class="btn btn-primary" id="create-shelf-btn" style="width:auto">
        ${Icons.plus} New Shelf
      </button>
    </div>

    <div id="create-shelf-form" class="create-shelf-form hidden">
      <input type="text" id="new-shelf-name" class="shelf-name-input"
        placeholder="Shelf name…" maxlength="128" />
      <button class="btn btn-primary btn-sm" id="create-shelf-submit" style="width:auto">Create</button>
      <button class="btn btn-outline btn-sm" id="create-shelf-cancel" style="width:auto">Cancel</button>
    </div>

    ${shelves.length === 0
      ? `<div class="empty-state">
           <div class="empty-state-icon">${Icons.shelf}</div>
           <h3>No shelves yet</h3>
           <p>Create a shelf to start a private reading group with encrypted books and reviews.</p>
         </div>`
      : renderShelvesContent(shelves)}
  </div>`;
}

function renderShelvesContent(shelves) {
  const activeId = state.activeShelfId ?? shelves[0]?.id;
  const activeShelf = shelves.find(s => s.id === activeId) || shelves[0];
  if (!activeShelf) return '';

  return `
  <div class="shelf-tabs-row">
    ${shelves.map(s => `
      <button class="shelf-tab-btn ${s.id === activeId ? 'active' : ''}" data-tab-shelf-id="${s.id}">
        ${Icons.shelf} ${escHtml(s.name)}
        ${s.is_owner ? '<span class="owner-dot" title="You own this shelf"></span>' : ''}
      </button>`).join('')}
  </div>

  <div id="shelf-panel">
    ${renderShelfPanel(activeShelf)}
  </div>`;
}

function renderSkeletonCards(n) {
  return Array.from({ length: n }, () => `
    <div class="skeleton-card">
      <div class="skeleton skeleton-cover"></div>
      <div class="skeleton-body">
        <div class="skeleton skeleton-line" style="width:90%"></div>
        <div class="skeleton skeleton-line" style="width:70%"></div>
      </div>
    </div>`).join('');
}

function renderShelfPanel(shelf) {
  const isOwner = shelf.owner_username === state.user?.username;
  const books = state.activeShelfBooks;

  return `
  <div class="shelf-panel-header">
    <span class="shelf-owner-chip">${Icons.user} ${escHtml(shelf.owner_username)}</span>
    ${isOwner ? `
      <button class="btn btn-outline btn-sm" id="manage-members-btn" data-shelf-id="${shelf.id}">
        ${Icons.admin} Members
      </button>` : ''}
  </div>

  <div class="shelf-add-bar">
    ${Icons.search.replace('<svg', '<svg class="shelf-add-search-icon"')}
    <input type="search" id="group-search-input" class="group-search-input"
      placeholder="Search to add a book to this shelf…" autocomplete="off" />
  </div>
  <div id="group-search-results" class="group-search-results"></div>

  <div class="book-grid" id="group-shelf-grid">
    ${state.loadingShelfBooks
      ? renderSkeletonCards(6)
      : books.length === 0
        ? `<div class="empty-state" style="grid-column:1/-1">
             <div class="empty-state-icon">${Icons.book}</div>
             <h3>No books yet</h3>
             <p>Search above to add the first book to this shelf.</p>
           </div>`
        : books.map(b => renderGroupShelfCard(b, shelf)).join('')}
  </div>

  <div id="members-panel" class="members-panel hidden"></div>`;
}

function renderGroupShelfCard(book, shelf) {
  const url = book.cover_id ? coverUrl(book.cover_id) : workCoverUrl(book.work_id);
  const canDelete =
    book.added_by === state.user?.username || shelf.owner_username === state.user?.username;
  const saved = book.work_id && isReadLater(book.work_id);
  const colorIdx = state.myShelves.findIndex(s => s.id === shelf.id);
  const shelfColor = SHELF_COLORS[colorIdx >= 0 ? colorIdx % SHELF_COLORS.length : 0];

  return `
  <div class="book-card shelf-color-card"
    style="--sc:${shelfColor}"
    data-work-id="${escHtml(book.work_id || '')}"
    data-title="${escHtml(book.title || '')}"
    data-book-id="${book.id}"
    data-shelf-id="${shelf.id}">
    ${renderCoverImg(url, book.title || 'Unknown')}
    <div class="book-info">
      <div class="book-title">${escHtml(book.title || 'Unknown Title')}</div>
      ${book.author ? `<div class="book-author">${escHtml(book.author)}</div>` : ''}
      <div class="book-meta">
        <div class="book-added-by">${Icons.user} ${escHtml(book.added_by || '?')}</div>
        ${book.year ? `<span class="book-year">${escHtml(String(book.year))}</span>` : ''}
      </div>
    </div>
    <div class="card-actions">
      <button class="btn btn-outline btn-sm group-review-btn"
        data-book-id="${book.id}" data-shelf-id="${shelf.id}"
        data-work-id="${escHtml(book.work_id || '')}"
        data-title="${escHtml(book.title || '')}">
        ${Icons.info} Reviews
      </button>
      <button class="btn ${saved ? 'btn-rl-saved' : 'btn-outline'} btn-sm group-rl-btn"
        data-work-id="${escHtml(book.work_id || '')}"
        title="${saved ? 'Remove from Read Later' : 'Save to Read Later'}">
        ${saved ? Icons.bookmarkFill : Icons.bookmark} ${saved ? 'Saved' : 'Read Later'}
      </button>
      <button class="btn btn-outline btn-sm group-go-link-btn"
        data-work-id="${escHtml(book.work_id || '')}"
        title="Open on OpenLibrary">
        ${Icons.external} Link
      </button>
      ${canDelete ? `
        <button class="btn btn-danger btn-sm group-delete-btn"
          data-book-id="${book.id}" data-shelf-id="${shelf.id}"
          data-title="${escHtml(book.title || '')}">
          ${Icons.trash} Delete
        </button>` : ''}
    </div>
  </div>`;
}
