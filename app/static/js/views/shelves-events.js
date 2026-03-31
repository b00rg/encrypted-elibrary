import { state } from '../state.js';
import { api } from '../api.js';
import { showToast } from '../toast.js';
import { loadMyShelves, loadActiveShelfBooks } from '../data.js';
import { refreshPageBody } from '../app.js';
import { doGroupSearch } from './shelves-search.js';
import { openMembersPanel } from './shelves-members.js';
import { openReviewModal } from './shelves-reviews.js';
import { toggleReadLater } from '../readLater.js';
import { openLibraryUrl } from '../utils.js';

export function bindShelvesEvents() {
  // Create shelf toggle
  document.getElementById('create-shelf-btn')?.addEventListener('click', () => {
    document.getElementById('create-shelf-form').classList.remove('hidden');
    document.getElementById('new-shelf-name').focus();
  });
  document.getElementById('create-shelf-cancel')?.addEventListener('click', () => {
    document.getElementById('create-shelf-form').classList.add('hidden');
    document.getElementById('new-shelf-name').value = '';
  });
  document.getElementById('create-shelf-submit')?.addEventListener('click', doCreateShelf);
  document.getElementById('new-shelf-name')?.addEventListener('keydown', e => {
    if (e.key === 'Enter') doCreateShelf();
  });

  // Shelf tabs
  document.querySelectorAll('[data-tab-shelf-id]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const id = parseInt(btn.dataset.tabShelfId, 10);
      state.activeShelfId = id;
      state.activeShelfBooks = [];
      state.loadingShelfBooks = true;
      refreshPageBody();
      await loadActiveShelfBooks();
      refreshPageBody();
      bindShelvesEvents();
    });
  });

  // Manage members
  document.getElementById('manage-members-btn')?.addEventListener('click', () => {
    const shelfId = parseInt(
      document.getElementById('manage-members-btn').dataset.shelfId, 10
    );
    openMembersPanel(shelfId);
  });

  // Inline book search
  const gsi = document.getElementById('group-search-input');
  if (gsi) {
    let debounce;
    gsi.addEventListener('input', e => {
      clearTimeout(debounce);
      const q = e.target.value.trim();
      if (!q) {
        document.getElementById('group-search-results').innerHTML = '';
        return;
      }
      debounce = setTimeout(() => doGroupSearch(q, bindShelvesEvents), 420);
    });
  }

  // Book grid: reviews + delete
  const grid = document.getElementById('group-shelf-grid');
  if (grid) {
    grid.addEventListener('click', e => {
      const reviewBtn = e.target.closest('.group-review-btn');
      const deleteBtn = e.target.closest('.group-delete-btn');

      const rlBtn     = e.target.closest('.group-rl-btn');
      const goLinkBtn = e.target.closest('.group-go-link-btn');

      if (reviewBtn) {
        e.stopPropagation();
        openReviewModal({
          shelfId: parseInt(reviewBtn.dataset.shelfId, 10),
          bookId:  parseInt(reviewBtn.dataset.bookId, 10),
          title:   reviewBtn.dataset.title,
        });
        return;
      }
      if (rlBtn) {
        e.stopPropagation();
        const workId = rlBtn.dataset.workId;
        const nowSaved = toggleReadLater(workId);
        showToast(nowSaved ? 'Added to Read Later.' : 'Removed from Read Later.', 'success');
        refreshPageBody();
        bindShelvesEvents();
        return;
      }
      if (goLinkBtn) {
        e.stopPropagation();
        window.open(openLibraryUrl(goLinkBtn.dataset.workId), '_blank', 'noopener');
        return;
      }
      if (deleteBtn) {
        e.stopPropagation();
        doDeleteBook(
          parseInt(deleteBtn.dataset.bookId, 10),
          parseInt(deleteBtn.dataset.shelfId, 10),
          deleteBtn.dataset.title
        );
      }
    });
  }
}

async function doCreateShelf() {
  const input = document.getElementById('new-shelf-name');
  const name = input?.value.trim();
  if (!name) { showToast('Shelf name required', 'error'); return; }

  const { ok, data } = await api('/shelves', {
    method: 'POST',
    body: JSON.stringify({ name }),
  });

  if (ok) {
    showToast(`Shelf "${name}" created!`, 'success');
    input.value = '';
    document.getElementById('create-shelf-form').classList.add('hidden');
    state.activeShelfId = data.id;
    state.activeShelfBooks = [];
    await loadMyShelves();
    refreshPageBody();
    bindShelvesEvents();
  } else {
    showToast(data.error || 'Failed to create shelf', 'error');
  }
}

async function doDeleteBook(bookId, shelfId, title) {
  if (!confirm(`Remove "${title}" from this shelf?`)) return;

  const { ok, data } = await api(`/shelves/${shelfId}/books/${bookId}`, { method: 'DELETE' });
  if (ok) {
    showToast(`"${title}" removed from shelf.`, 'success');
    state.activeShelfBooks = state.activeShelfBooks.filter(b => b.id !== bookId);
    refreshPageBody();
    bindShelvesEvents();
  } else {
    showToast(data.error || 'Failed to remove book', 'error');
  }
}
