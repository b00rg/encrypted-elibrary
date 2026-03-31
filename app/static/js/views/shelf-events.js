import { state } from '../state.js';
import { toggleReadLater } from '../readLater.js';
import { showToast } from '../toast.js';
import { bindSearchResultEvents } from './search.js';
import { refreshPageBody, switchToMyShelves } from '../app.js';
import { openLibraryUrl } from '../utils.js';
import { api } from '../api.js';

export function bindShelfEvents() {
  document.getElementById('filter-all')?.addEventListener('click', () => {
    state.readLaterFilter = false;
    refreshPageBody();
  });

  document.getElementById('filter-rl')?.addEventListener('click', () => {
    state.readLaterFilter = true;
    refreshPageBody();
  });

  document.getElementById('toggle-enc-global')?.addEventListener('click', () => {
    state.showEncryptedReviews = !state.showEncryptedReviews;
    refreshPageBody();
    bindShelfEvents();
  });

  // Shelf nav tabs → navigate to that shelf
  document.querySelectorAll('.shelf-nav-tab').forEach(btn => {
    btn.addEventListener('click', () => {
      const id = parseInt(btn.dataset.shelfNavId, 10);
      state.activeShelfId = id;
      switchToMyShelves();
    });
  });

  const grid = document.getElementById('shelf-grid');
  if (!grid) return;

  grid.addEventListener('click', async e => {
    const goLinkBtn = e.target.closest('.shelf-card-go-link');
    if (goLinkBtn) {
      e.stopPropagation();
      window.open(openLibraryUrl(goLinkBtn.dataset.workId), '_blank', 'noopener');
      return;
    }

    const rlBtn = e.target.closest('.rl-btn');
    if (rlBtn) {
      e.stopPropagation();
      const workId = rlBtn.dataset.workId;
      const nowSaved = toggleReadLater(workId);
      showToast(nowSaved ? 'Added to Read Later.' : 'Removed from Read Later.', 'success');
      if (!nowSaved && state.readLaterFilter) {
        // Remove from cached reviews only if needed to keep filter clean
        const newReviews = { ...state.readLaterReviews };
        delete newReviews[workId];
        state.readLaterReviews = newReviews;
      }
      refreshPageBody();
      if (state.searchQuery) bindSearchResultEvents();
      return;
    }

    const deleteBtn = e.target.closest('.shared-delete-btn');
    if (deleteBtn) {
      e.stopPropagation();
      const bookId = parseInt(deleteBtn.dataset.bookId, 10);
      const title = deleteBtn.dataset.title;
      if (!confirm(`Remove "${title}" from the shared shelf?`)) return;
      const { ok } = await api(`/shelf/books/${bookId}`, { method: 'DELETE' });
      if (ok) {
        state.shelfBooks = state.shelfBooks.filter(b => b.id !== bookId);
        refreshPageBody();
        bindShelfEvents();
        showToast('Book removed from shelf.', 'success');
      } else {
        showToast('Failed to remove book.', 'error');
      }
      return;
    }
  });
}
