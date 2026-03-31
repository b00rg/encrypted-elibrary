import { Icons } from '../icons.js';
import { escHtml } from '../utils.js';
import { state } from '../state.js';
import { api } from '../api.js';
import { showToast } from '../toast.js';

export async function openMembersPanel(shelfId) {
  const panel = document.getElementById('members-panel');
  if (!panel) return;
  panel.classList.remove('hidden');
  panel.innerHTML = `<div style="padding:20px;text-align:center"><div class="spinner spinner-dark"></div></div>`;

  const { ok, data } = await api(`/shelves/${shelfId}/members`);
  if (!ok) { panel.innerHTML = `<p style="padding:16px">Could not load members.</p>`; return; }

  const members = data.members || [];
  panel.innerHTML = `
  <div class="members-panel-header">
    <h3 class="members-panel-title">${Icons.admin} Members</h3>
    <button class="btn btn-outline btn-sm" id="close-members-btn">Close</button>
  </div>
  <div class="members-list">
    ${members.map(m => `
      <div class="member-row">
        <span class="member-name">${Icons.user} ${escHtml(m.username)}</span>
        ${m.username === state.user?.username ? '' : `
          <button class="btn btn-danger btn-sm remove-member-btn"
            data-shelf-id="${shelfId}" data-username="${escHtml(m.username)}">
            ${Icons.trash}
          </button>`}
      </div>`).join('')}
  </div>
  <div class="add-member-row">
    <input type="text" id="add-member-input" class="add-member-input"
      placeholder="Username to add…" />
    <button class="btn btn-primary btn-sm" id="add-member-btn"
      data-shelf-id="${shelfId}" style="width:auto">
      ${Icons.plus} Add
    </button>
  </div>`;

  document.getElementById('close-members-btn')?.addEventListener('click', () => {
    panel.classList.add('hidden');
  });

  document.getElementById('add-member-btn')?.addEventListener('click', async () => {
    const username = document.getElementById('add-member-input')?.value.trim();
    if (!username) return;
    const { ok, data } = await api(`/shelves/${shelfId}/members`, {
      method: 'POST',
      body: JSON.stringify({ username }),
    });
    if (ok) {
      showToast(`${username} added!`, 'success');
      openMembersPanel(shelfId);
    } else {
      showToast(data.error || 'Failed to add member', 'error');
    }
  });

  panel.querySelectorAll('.remove-member-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const username = btn.dataset.username;
      if (!confirm(`Remove ${username} from this shelf? This will re-encrypt the shelf key.`)) return;
      const { ok, data } = await api(
        `/shelves/${shelfId}/members/${encodeURIComponent(username)}`,
        { method: 'DELETE' }
      );
      if (ok) {
        showToast(`${username} removed and shelf re-keyed.`, 'success');
        openMembersPanel(shelfId);
      } else {
        showToast(data.error || 'Failed to remove member', 'error');
      }
    });
  });
}
