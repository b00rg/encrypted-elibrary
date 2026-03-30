import { Icons } from '../icons.js';
import { escHtml } from '../utils.js';
import { api } from '../api.js';
import { showToast } from '../toast.js';
// loadInitialView is imported from app.js; the circular reference is safe because
// this import is only used inside event handler callbacks (not at module init time).
import { loadInitialView } from '../app.js';

export function renderAuthPage() {
  return `
  <div class="auth-page">
    <div class="auth-card">
      <div class="auth-header">
        <div class="auth-logo">${Icons.book} Bookshelf</div>
        <p class="auth-tagline">A shared encrypted library for curious minds.</p>
      </div>

      <div class="auth-tabs">
        <button class="auth-tab active" data-tab="login">Sign In</button>
        <button class="auth-tab"        data-tab="register">Create Account</button>
      </div>

      <div class="auth-body">
        <div id="tab-login">
          <form class="auth-form" id="login-form" novalidate>
            <div class="form-group">
              <label class="form-label" for="login-username">Username</label>
              <input class="form-input" id="login-username" type="text"
                placeholder="your username" autocomplete="username" required />
            </div>
            <div class="form-group">
              <label class="form-label" for="login-password">Password</label>
              <input class="form-input" id="login-password" type="password"
                placeholder="••••••••" autocomplete="current-password" required />
            </div>
            <div id="login-error" class="form-error" style="display:none"></div>
            <button type="submit" class="btn btn-primary" id="login-btn">
              Sign In
            </button>
          </form>
        </div>

        <div id="tab-register" style="display:none">
          <form class="auth-form" id="register-form" novalidate>
            <div class="form-group">
              <label class="form-label" for="reg-username">Username</label>
              <input class="form-input" id="reg-username" type="text"
                placeholder="choose a username" autocomplete="username" required />
            </div>
            <div class="form-group">
              <label class="form-label" for="reg-password">Password</label>
              <input class="form-input" id="reg-password" type="password"
                placeholder="at least 6 characters" autocomplete="new-password" required />
            </div>
            <div class="form-group">
              <label class="form-label" for="reg-confirm">Confirm Password</label>
              <input class="form-input" id="reg-confirm" type="password"
                placeholder="repeat your password" autocomplete="new-password" required />
            </div>
            <div id="reg-error" class="form-error" style="display:none"></div>
            <button type="submit" class="btn btn-primary" id="register-btn">
              Create Account
            </button>
          </form>
        </div>
      </div>
    </div>
  </div>`;
}

export function bindAuthEvents() {
  document.querySelectorAll('.auth-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.auth-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      const name = tab.dataset.tab;
      document.getElementById('tab-login').style.display    = name === 'login'    ? '' : 'none';
      document.getElementById('tab-register').style.display = name === 'register' ? '' : 'none';
    });
  });

  document.getElementById('login-form')?.addEventListener('submit', async e => {
    e.preventDefault();
    const btn = document.getElementById('login-btn');
    const errEl = document.getElementById('login-error');
    const username = document.getElementById('login-username').value.trim();
    const password = document.getElementById('login-password').value;

    errEl.style.display = 'none';
    if (!username || !password) {
      errEl.textContent = 'Please fill in all fields.'; errEl.style.display = ''; return;
    }
    btn.disabled = true;
    btn.innerHTML = `<div class="spinner"></div> Signing in…`;

    const { ok, data } = await api('/login', {
      method: 'POST', body: JSON.stringify({ username, password }),
    });
    if (ok) {
      await loadInitialView();
    } else {
      errEl.textContent = data.error || 'Login failed.';
      errEl.style.display = '';
      btn.disabled = false;
      btn.textContent = 'Sign In';
    }
  });

  document.getElementById('register-form')?.addEventListener('submit', async e => {
    e.preventDefault();
    const btn = document.getElementById('register-btn');
    const errEl = document.getElementById('reg-error');
    const username = document.getElementById('reg-username').value.trim();
    const password = document.getElementById('reg-password').value;
    const confirm  = document.getElementById('reg-confirm').value;

    errEl.style.display = 'none';
    if (!username || !password) {
      errEl.textContent = 'Please fill in all fields.'; errEl.style.display = ''; return;
    }
    if (password.length < 6) {
      errEl.textContent = 'Password must be at least 6 characters.'; errEl.style.display = ''; return;
    }
    if (password !== confirm) {
      errEl.textContent = 'Passwords do not match.'; errEl.style.display = ''; return;
    }

    btn.disabled = true;
    btn.innerHTML = `<div class="spinner"></div> Creating account…`;

    const { ok, data } = await api('/register', {
      method: 'POST', body: JSON.stringify({ username, password }),
    });
    if (ok) {
      showToast('Account created! Please sign in.', 'success');
      document.querySelectorAll('.auth-tab').forEach(t => t.classList.remove('active'));
      document.querySelector('[data-tab="login"]').classList.add('active');
      document.getElementById('tab-login').style.display = '';
      document.getElementById('tab-register').style.display = 'none';
      document.getElementById('login-username').value = username;
      btn.disabled = false;
      btn.textContent = 'Create Account';
    } else {
      errEl.textContent = data.error || 'Registration failed.';
      errEl.style.display = '';
      btn.disabled = false;
      btn.textContent = 'Create Account';
    }
  });
}
