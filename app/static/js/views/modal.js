import { Icons } from '../icons.js';
import { escHtml, openLibraryUrl, workCoverUrl } from '../utils.js';
import { api } from '../api.js';
import { showToast } from '../toast.js';
import { loadShelfBooks } from '../data.js';

export function closeModal() {
  document.getElementById('modal-overlay').classList.add('hidden');
}

export function openBookModal(book) {
  const overlay = document.getElementById('modal-overlay');
  const content = document.getElementById('modal-content');
  const url = book.cover || (book.work_id ? workCoverUrl(book.work_id) : null);

  content.innerHTML = `
  <div class="modal-book">
    <div class="modal-cover-wrap">
      ${url
        ? `<img src="${escHtml(url)}" alt="${escHtml(book.title)}"
            onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">
           <div class="modal-cover-placeholder" style="display:none">${Icons.book}</div>`
        : `<div class="modal-cover-placeholder">${Icons.book}</div>`}
    </div>
    <div class="modal-body">
      <div class="modal-title">${escHtml(book.title || 'Unknown Title')}</div>
      ${book.author ? `<div class="modal-author">${escHtml(book.author)}</div>` : ''}

      <div class="modal-meta-row">
        ${book.year    ? `<span class="modal-chip">${Icons.clock} ${escHtml(String(book.year))}</span>` : ''}
        ${book.added_by ? `<span class="modal-chip">${Icons.user} Added by ${escHtml(book.added_by)}</span>` : ''}
      </div>

      ${book.description
        ? `<p class="modal-desc">${escHtml(book.description)}</p>`
        : `<p class="modal-desc" style="font-style:italic;opacity:0.5">No description available.</p>`}

      <div class="modal-actions">
        ${book.fromShelf
          ? `<a class="btn btn-outline" href="${escHtml(openLibraryUrl(book.work_id))}"
               target="_blank" rel="noopener noreferrer">
               ${Icons.external} View on OpenLibrary
             </a>`
          : `<button class="btn btn-primary" id="modal-add-btn"
               data-work-id="${escHtml(book.work_id)}" data-title="${escHtml(book.title)}">
               ${Icons.plus} Add to Shelf
             </button>
             <a class="btn btn-outline" href="${escHtml(openLibraryUrl(book.work_id))}"
               target="_blank" rel="noopener noreferrer">
               ${Icons.external} OpenLibrary
             </a>`}
      </div>
    </div>
  </div>`;

  overlay.classList.remove('hidden');

  document.getElementById('modal-add-btn')?.addEventListener('click', async () => {
    const btn = document.getElementById('modal-add-btn');
    const workId = btn.dataset.workId;
    const title  = btn.dataset.title;
    btn.disabled = true;
    btn.innerHTML = `<div class="spinner"></div> Adding…`;

    const { ok, data } = await api('/shelf/add', {
      method: 'POST', body: JSON.stringify({ work_id: workId }),
    });
    if (ok) {
      showToast(`"${title}" added to the shelf!`, 'success');
      closeModal();
      await loadShelfBooks();
      document.querySelectorAll(`.search-add-btn[data-work-id="${CSS.escape(workId)}"]`)
        .forEach(b => {
          b.disabled = true;
          b.innerHTML = `${Icons.check} Added`;
          b.classList.remove('btn-primary'); b.classList.add('btn-outline');
        });
    } else {
      showToast(data.error || 'Failed to add book.', 'error');
      btn.disabled = false;
      btn.innerHTML = `${Icons.plus} Add to Shelf`;
    }
  });
}
