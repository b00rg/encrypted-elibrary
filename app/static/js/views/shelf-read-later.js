import { Icons } from '../icons.js';
import { escHtml, coverUrl, workCoverUrl, renderCoverImg } from '../utils.js';
import { state } from '../state.js';

export function renderReadLaterRow(book) {
  const url = book.cover_id ? coverUrl(book.cover_id) : workCoverUrl(book.work_id);
  return `
  <div class="rl-book-row">
    <div class="rl-book-header">
      <div class="rl-cover-wrap">
        ${renderCoverImg(url, book.title, 'rl-cover')}
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
        <button class="btn btn-outline btn-sm shelf-card-details"
          data-work-id="${escHtml(book.work_id)}"
          data-title="${escHtml(book.title)}"
          data-author="${escHtml(book.author || '')}"
          data-cover="${escHtml(url)}"
          data-desc="${escHtml(book.description || '')}"
          data-year="${escHtml(String(book.year || ''))}"
          data-added="${escHtml(book.added_by || '')}">
          ${Icons.external}
        </button>
        <button class="btn btn-rl-saved btn-sm rl-btn"
          data-work-id="${escHtml(book.work_id)}"
          title="Remove from Read Later">
          ${Icons.bookmarkFill} Saved
        </button>
      </div>
    </div>

    <div class="rl-reviews-section">
      ${renderReadLaterReviews(book.work_id)}
    </div>
  </div>`;
}

function renderReadLaterReviews(workId) {
  if (state.loadingReadLaterReviews) {
    return `<div class="rl-reviews-loading">
      <div class="spinner spinner-dark"></div> Loading reviews…
    </div>`;
  }

  const groups = state.readLaterReviews[workId];
  if (!groups) {
    return `<div class="rl-reviews-empty">
      Switch to a shelf and add this book to see reviews here.
    </div>`;
  }
  if (groups.length === 0) {
    return `<div class="rl-reviews-empty">No reviews from your shelves for this book.</div>`;
  }

  return groups.map(group => `
    <div class="rl-reviews-group">
      <div class="rl-reviews-shelf-name">${Icons.shelf} ${escHtml(group.shelf_name)}</div>
      ${group.reviews.length === 0
        ? `<div class="rl-reviews-empty" style="padding:8px 0 0">No reviews yet on this shelf.</div>`
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
    </div>`).join('');
}
