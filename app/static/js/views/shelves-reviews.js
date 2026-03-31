import { Icons } from '../icons.js';
import { escHtml } from '../utils.js';
import { api } from '../api.js';
import { showToast } from '../toast.js';

export async function openReviewModal({ shelfId, bookId, title }) {
  const overlay = document.getElementById('modal-overlay');
  const content = document.getElementById('modal-content');

  content.innerHTML = `
  <div class="modal-body" style="padding:40px;text-align:center">
    <div class="spinner spinner-dark" style="width:32px;height:32px;margin:0 auto 16px"></div>
    <p style="color:var(--text-muted)">Loading reviews…</p>
  </div>`;
  overlay.classList.remove('hidden');

  let showEncrypted = false;

  async function fetchAndRender() {
    const { ok, data } = await api(`/shelves/${shelfId}/books/${bookId}/reviews`);
    const reviews = ok ? (data.reviews || []) : [];
    renderReviews(reviews);
  }

  function renderReviews(reviews) {
    content.innerHTML = `
    <div class="modal-body review-modal">
      <div class="modal-title" style="margin-bottom:8px">${escHtml(title)}</div>
      <div class="review-section-header">
        <h3 class="review-section-title">${Icons.info} Reviews (${reviews.length})</h3>
        <button class="btn btn-outline btn-sm" id="toggle-enc-modal">
          ${showEncrypted ? '🔓 Decrypted' : '🔒 Encrypted'}
        </button>
      </div>

      ${reviews.length === 0
        ? `<p class="no-reviews-msg">No reviews yet. Be the first!</p>`
        : reviews.map(r => `
          <div class="review-card">
            <div class="review-header">
              <span class="review-author">${Icons.user} ${escHtml(r.reviewer_username)}</span>
              <span class="review-date">${escHtml(r.created_at)}</span>
            </div>
            ${showEncrypted
              ? `<div class="review-enc-text">${escHtml(r.review_enc)}</div>`
              : `<div class="review-text">${escHtml(r.review || '[Could not decrypt]')}</div>`}
          </div>`).join('')}

      <div class="review-form">
        <h4 class="review-form-title">Write a Review</h4>
        <textarea id="review-textarea" class="review-textarea"
          placeholder="Share your thoughts on this book…" rows="4"></textarea>
        <button class="btn btn-primary" id="post-review-btn" style="margin-top:8px">
          Post Review
        </button>
      </div>
    </div>`;

    document.getElementById('toggle-enc-modal')?.addEventListener('click', () => {
      showEncrypted = !showEncrypted;
      fetchAndRender();
    });

    document.getElementById('post-review-btn')?.addEventListener('click', async () => {
      const text = document.getElementById('review-textarea')?.value.trim();
      if (!text) { showToast('Review cannot be empty', 'error'); return; }

      const btn = document.getElementById('post-review-btn');
      btn.disabled = true;
      btn.innerHTML = `<div class="spinner"></div> Posting…`;

      const { ok, data } = await api(`/shelves/${shelfId}/books/${bookId}/reviews`, {
        method: 'POST',
        body: JSON.stringify({ review: text }),
      });

      if (ok) {
        showToast('Review posted!', 'success');
        fetchAndRender();
      } else {
        showToast(data.error || 'Failed to post review', 'error');
        btn.disabled = false;
        btn.innerHTML = 'Post Review';
      }
    });
  }

  await fetchAndRender();
}
