import { Icons } from './icons.js';
import { escHtml } from './utils.js';

export function showToast(message, type = 'default') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;

  const iconMap = { success: Icons.check, error: Icons.warning, default: Icons.info };
  toast.innerHTML = `${iconMap[type] || iconMap.default}<span>${escHtml(message)}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.animation = 'toastOut 0.3s ease both';
    setTimeout(() => toast.remove(), 300);
  }, 3200);
}
