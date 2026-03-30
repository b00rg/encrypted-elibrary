import { state } from './state.js';
import { showToast } from './toast.js';

// Registered by app.js to avoid a circular import at init time.
let _onForceLogout = () => {};
export function setForceLogoutHandler(fn) { _onForceLogout = fn; }

export async function api(path, options = {}) {
  try {
    const res = await fetch('/api' + path, {
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      ...options,
    });
    const data = await res.json().catch(() => ({}));
    if (res.status === 401 && state.view !== 'auth') {
      _onForceLogout();
      return { ok: false, status: 401, data };
    }
    return { ok: res.ok, status: res.status, data };
  } catch {
    showToast('Network error — check your connection.', 'error');
    return { ok: false, status: 0, data: { error: 'Network error' } };
  }
}
