import { Icons } from '../icons.js';

export function renderPendingPage() {
  return `
  <div class="pending-card">
    <div class="pending-icon">${Icons.clock}</div>
    <h2>You're on the list</h2>
    <p>Your account has been created, but you haven't been added to the shared shelf yet.<br><br>
       Ask an administrator to grant you access. Once added, log out and back in to unlock the shelf.</p>
    <button class="btn btn-outline" id="pending-logout" style="margin-top:28px">
      ${Icons.logout} Sign out
    </button>
  </div>`;
}
