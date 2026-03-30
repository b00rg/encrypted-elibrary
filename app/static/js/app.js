import { state } from './state.js';
import { api, setForceLogoutHandler } from './api.js';
import { showToast } from './toast.js';
import { loadShelfBooks, loadAdminUsers } from './data.js';
import { renderHeader, bindHeaderEvents } from './views/header.js';
import { renderAuthPage, bindAuthEvents } from './views/auth.js';
import { renderShelfPage, bindShelfEvents } from './views/shelf.js';
import { bindSearchResultEvents } from './views/search.js';
import { renderAdminPage, bindAdminEvents } from './views/admin.js';
import { renderPendingPage } from './views/pending.js';
import { closeModal } from './views/modal.js';

// ── App Root ──────────────────────────────────────────────────────────
export function renderApp() {
  const app = document.getElementById('app');

  if (state.view === 'auth') {
    app.innerHTML = renderAuthPage();
    bindAuthEvents();
    return;
  }

  app.innerHTML = `
    ${renderHeader()}
    <main class="main-content">
      <div class="container" id="page-body">
        ${state.view === 'shelf'   ? renderShelfPage()   : ''}
        ${state.view === 'pending' ? renderPendingPage() : ''}
        ${state.view === 'admin'   ? renderAdminPage()   : ''}
      </div>
    </main>`;

  bindHeaderEvents();
  if (state.view === 'shelf')  bindShelfEvents();
  if (state.view === 'admin')  bindAdminEvents();
  if (state.view === 'pending') {
    document.getElementById('pending-logout')?.addEventListener('click', doLogout);
  }
}

// ── Navigation ────────────────────────────────────────────────────────
export function refreshPageBody() {
  const body = document.getElementById('page-body');
  if (!body) return;

  if (state.view === 'shelf') {
    body.innerHTML = renderShelfPage();
    bindShelfEvents();
    if (state.searchQuery) bindSearchResultEvents();
  } else if (state.view === 'admin') {
    body.innerHTML = renderAdminPage();
    bindAdminEvents();
  }
}

export async function switchToShelf() {
  state.view = 'shelf';
  state.searchQuery = '';
  state.searchResults = [];
  state.loadingShelf = true;
  renderApp();

  await loadShelfBooks();
  state.loadingShelf = false;
  refreshPageBody();
}

export async function switchToAdmin() {
  state.view = 'admin';
  renderApp();
  await loadAdminUsers();
  refreshPageBody();
  bindAdminEvents();
}

export async function loadInitialView() {
  const { ok, data: meData } = await api('/me');
  if (!ok || !meData) {
    state.view = 'auth';
    renderApp();
    return;
  }

  state.user = meData;

  const { ok: shelfOk, data: shelfData } = await api('/shelf');
  if (!shelfOk) {
    state.view = 'auth'; renderApp(); return;
  }

  if (!shelfData.is_member) {
    state.view = 'pending'; renderApp(); return;
  }

  state.view = 'shelf';
  state.loadingShelf = true;
  renderApp();

  const withDetails = await Promise.all(
    (shelfData.books || []).map(async b => {
      if (!b.work_id) return { ...b, title: '[Encrypted]', author: '', description: '' };
      const { ok: dok, data: detail } = await api('/shelf/book/' + encodeURIComponent(b.work_id));
      return dok ? { ...b, ...detail } : { ...b, title: b.work_id, description: '' };
    })
  );
  state.shelfBooks = withDetails.reverse();
  state.loadingShelf = false;
  refreshPageBody();
}

export async function doLogout() {
  await api('/logout');
  state.user = null;
  state.shelfBooks = [];
  state.searchResults = [];
  state.searchQuery = '';
  state.view = 'auth';
  renderApp();
}

function forceLogout() {
  state.user = null;
  state.shelfBooks = [];
  state.searchResults = [];
  state.searchQuery = '';
  state.searchLoading = false;
  state.view = 'auth';
  showToast('Your session expired. Please sign in again.', 'error');
  renderApp();
}

setForceLogoutHandler(forceLogout);

// ── Init ──────────────────────────────────────────────────────────────
async function init() {
  const loading = document.getElementById('loading-screen');

  await loadInitialView();

  if (loading) {
    loading.style.opacity = '0';
    setTimeout(() => loading.remove(), 400);
  }

  document.addEventListener('keydown', e => {
    if (e.key === '/' && document.activeElement?.tagName !== 'INPUT') {
      e.preventDefault();
      document.getElementById('search-input')?.focus();
    }
    if (e.key === 'Escape') closeModal();
  });
}

init();
