/**
 * DonasiKita - Authentication State & Navbar Manager
 * Syncs client-side state with backend session, handles role guards,
 * and renders user menu navigation.
 */

const Auth = {
  TOKEN_KEY: 'dk_session_token',
  USER_KEY: 'dk_user',

  getToken() {
    const params = new URLSearchParams(window.location.search);
    const urlToken = params.get('session_token');
    if (urlToken) {
      localStorage.setItem(this.TOKEN_KEY, urlToken);
      const urlRole = params.get('role');
      const urlName = params.get('name') || 'Administrator';
      if (urlRole) {
        localStorage.setItem(this.USER_KEY, JSON.stringify({
          role: urlRole,
          full_name: urlName,
          email: `${urlRole}@donasikita.id`
        }));
      }
      return urlToken;
    }
    return localStorage.getItem(this.TOKEN_KEY);
  },

  getUser() {
    const u = localStorage.getItem(this.USER_KEY);
    return u ? JSON.parse(u) : null;
  },

  setSession(token, user) {
    localStorage.setItem(this.TOKEN_KEY, token);
    localStorage.setItem(this.USER_KEY, JSON.stringify(user));
  },

  clearSession() {
    localStorage.removeItem(this.TOKEN_KEY);
    localStorage.removeItem(this.USER_KEY);
  },

  isLoggedIn() {
    return !!this.getToken();
  },

  hasRole(roles) {
    const user = this.getUser();
    if (!user) return false;
    if (typeof roles === 'string') roles = [roles];
    return roles.includes(user.role);
  },

  async logout() {
    const token = this.getToken();
    if (token) {
      try {
        await API.logout(token);
      } catch (e) {
        console.warn("Logout error:", e);
      }
    }
    this.clearSession();
    Utils.showToast("Anda telah keluar.", "success");
    setTimeout(() => {
      window.location.href = "/index.html";
    }, 500);
  },

  /**
   * Initializes navbar user UI state across all pages.
   */
  async initNavbar() {
    const navActions = document.getElementById('navbarUserActions');
    if (!navActions) return;

    const token = this.getToken();
    let user = this.getUser();

    // Verify token with backend if exists
    if (token) {
      try {
        const res = await API.getCurrentUser(token);
        if (res.success && res.user) {
          user = res.user;
          localStorage.setItem(this.USER_KEY, JSON.stringify(user));
        } else {
          // Token expired or invalid
          this.clearSession();
          user = null;
        }
      } catch (e) {
        console.warn("Session check error:", e);
      }
    }

    if (!user) {
      // Guest view
      navActions.innerHTML = `
        <a href="/pages/login.html" class="btn btn-secondary btn-sm" id="navBtnLogin">Masuk</a>
        <a href="/pages/register.html" class="btn btn-primary btn-sm" id="navBtnRegister">Daftar</a>
      `;
      return;
    }

    // Role-specific dashboard link
    let dashboardHref = "/pages/dashboard_donatur.html";
    let dashboardLabel = "Dashboard Donatur";
    if (user.role === 'admin') {
      dashboardHref = "/pages/dashboard_admin.html";
      dashboardLabel = "Dashboard Admin";
    } else if (user.role === 'fundraiser') {
      dashboardHref = "/pages/dashboard_fundraiser.html";
      dashboardLabel = "Dashboard Penggalang Dana";
    }

    const avatarSrc = `/assets/images/${user.avatar || 'default_avatar.png'}`;
    const initials = (user.full_name || 'U').substring(0, 2).toUpperCase();

    navActions.innerHTML = `
      <div class="user-menu-pill" id="userMenuToggle" onclick="Auth.toggleUserDropdown()">
        <img src="${avatarSrc}" alt="${user.full_name}" class="user-menu-avatar" onerror="this.outerHTML='<div class=\\'user-menu-avatar\\'>${initials}</div>'">
        <span class="user-menu-name">${user.full_name}</span>
        <span class="user-menu-role">${user.role}</span>
        <span style="font-size: 10px; color: var(--color-text-subtle);">▼</span>

        <div class="dropdown-menu" id="userDropdownMenu">
          <a href="${dashboardHref}" class="dropdown-item">
            <span>📊</span> ${dashboardLabel}
          </a>
          ${user.role === 'fundraiser' ? `
            <a href="/pages/campaign_form.html" class="dropdown-item">
              <span>➕</span> Buat Campaign
            </a>
          ` : ''}
          <div class="dropdown-divider"></div>
          <button type="button" class="dropdown-item" style="width:100%; text-align:left; background:none; border:none; cursor:pointer;" onclick="Auth.logout()">
            <span style="color:var(--color-danger)">🚪</span> Keluar
          </button>
        </div>
      </div>
    `;

    // Close dropdown on outside click
    document.addEventListener('click', (e) => {
      const toggle = document.getElementById('userMenuToggle');
      const dropdown = document.getElementById('userDropdownMenu');
      if (toggle && dropdown && !toggle.contains(e.target)) {
        dropdown.classList.remove('show');
      }
    });
  },

  toggleUserDropdown() {
    const dropdown = document.getElementById('userDropdownMenu');
    if (dropdown) {
      dropdown.classList.toggle('show');
    }
  },

  /**
   * Enforces page access rules for protected dashboards.
   */
  guard(allowedRoles = []) {
    if (!this.isLoggedIn()) {
      Utils.showToast("Silakan login terlebih dahulu untuk mengakses halaman ini.", "warning");
      setTimeout(() => {
        window.location.href = `/pages/login.html?redirect=${encodeURIComponent(window.location.pathname + window.location.search)}`;
      }, 700);
      return false;
    }

    if (allowedRoles.length > 0 && !this.hasRole(allowedRoles)) {
      Utils.showToast("Akses ditolak: Akun Anda tidak memiliki izin untuk halaman ini.", "error");
      setTimeout(() => {
        window.location.href = "/index.html";
      }, 1000);
      return false;
    }

    return true;
  }
};
