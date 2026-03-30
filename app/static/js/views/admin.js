import { Icons } from '../icons.js';
import { escHtml, initials } from '../utils.js';
import { state } from '../state.js';
import { api } from '../api.js';
import { showToast } from '../toast.js';
import { loadAdminUsers } from '../data.js';
// refreshPageBody and switchToShelf are imported from app.js.
// The circular reference is safe: only called inside event handlers.
import { refreshPageBody, switchToShelf } from '../app.js';

export function renderAdminPage() {
  const users = state.adminUsers;
  const members = users.filter(u => u.is_member).length;

  return `
  <div>
    <div class="section-header">
      <div>
        <h1 class="section-title">Admin Panel</h1>
        <p class="section-subtitle">Manage shelf membership and user access.</p>
      </div>
      <button class="nav-btn nav-btn-ghost" id="back-to-shelf">
        ${Icons.shelf} Back to Shelf
      </button>
    </div>

    <div class="admin-stats">
      <div class="stat-card">
        <div class="stat-value">${users.length}</div>
        <div class="stat-label">Total Users</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">${members}</div>
        <div class="stat-label">Shelf Members</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">${users.length - members}</div>
        <div class="stat-label">Pending Access</div>
      </div>
    </div>

    <div class="users-table-wrapper">
      <table class="users-table">
        <thead>
          <tr>
            <th>User</th>
            <th>Status</th>
            <th>Role</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          ${users.map(u => renderUserRow(u)).join('')}
        </tbody>
      </table>
    </div>
  </div>`;
}

function renderUserRow(u) {
  const isSelf = u.username === state.user?.username;
  return `
  <tr data-username="${escHtml(u.username)}">
    <td>
      <div class="user-row-info">
        <div class="table-avatar">${escHtml(initials(u.username))}</div>
        <strong>${escHtml(u.username)}</strong>${isSelf ? ' <span style="font-size:0.75rem;color:var(--text-muted)">(you)</span>' : ''}
      </div>
    </td>
    <td>
      ${u.is_member
        ? `<span class="badge badge-member">${Icons.check} Member</span>`
        : `<span class="badge badge-pending">${Icons.clock} Pending</span>`}
    </td>
    <td>
      ${u.is_admin ? `<span class="badge badge-admin">${Icons.admin} Admin</span>` : '<span style="color:var(--text-muted);font-size:0.8rem">User</span>'}
    </td>
    <td>
      <div class="table-actions">
        ${!u.is_member
          ? `<button class="btn btn-outline btn-sm admin-add-btn" data-username="${escHtml(u.username)}">
               ${Icons.plus} Add to Shelf
             </button>`
          : ''}
        ${u.is_member && !isSelf
          ? `<button class="btn btn-danger btn-sm admin-remove-btn" data-username="${escHtml(u.username)}">
               ${Icons.trash} Remove
             </button>`
          : ''}
        ${isSelf ? '<span style="color:var(--text-muted);font-size:0.8rem">—</span>' : ''}
      </div>
    </td>
  </tr>`;
}

export function bindAdminEvents() {
  document.getElementById('back-to-shelf')?.addEventListener('click', () => switchToShelf());

  document.querySelectorAll('.admin-add-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const username = btn.dataset.username;
      btn.disabled = true;
      btn.innerHTML = `<div class="spinner spinner-dark"></div>`;
      const { ok, data } = await api('/admin/add', {
        method: 'POST', body: JSON.stringify({ username }),
      });
      if (ok) {
        showToast(`${username} added to the shelf.`, 'success');
        await loadAdminUsers();
        refreshPageBody();
        bindAdminEvents();
      } else {
        showToast(data.error || 'Failed to add user.', 'error');
        btn.disabled = false;
        btn.innerHTML = `${Icons.plus} Add to Shelf`;
      }
    });
  });

  document.querySelectorAll('.admin-remove-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const username = btn.dataset.username;
      if (!confirm(`Remove "${username}" from the shelf? Their access will be revoked and the shelf will be re-keyed.`)) return;
      btn.disabled = true;
      btn.innerHTML = `<div class="spinner"></div>`;
      const { ok, data } = await api('/admin/remove', {
        method: 'POST', body: JSON.stringify({ username }),
      });
      if (ok) {
        showToast(`${username} removed and shelf re-keyed.`, 'success');
        await loadAdminUsers();
        refreshPageBody();
        bindAdminEvents();
      } else {
        showToast(data.error || 'Failed to remove user.', 'error');
        btn.disabled = false;
        btn.innerHTML = `${Icons.trash} Remove`;
      }
    });
  });
}
