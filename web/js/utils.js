/**
 * DonasiKita - Utility & Helper Functions
 * Provides consistent Rupiah currency formatting, date parsing, and UI toasts.
 */

const Utils = {
  /**
   * Formats a numeric value into standard Indonesian Rupiah (e.g., Rp150.000, Rp2.500.000).
   * @param {number|string} amount 
   * @returns {string} Formatted string
   */
  formatRupiah(amount) {
    const num = Math.round(Number(amount) || 0);
    return 'Rp' + num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  },

  /**
   * Formats standard ISO/SQL date into Indonesian human readable format.
   * @param {string} dateStr e.g. "2026-10-19"
   * @returns {string} e.g. "19 Oktober 2026"
   */
  formatDate(dateStr) {
    if (!dateStr) return '-';
    try {
      const d = new Date(dateStr);
      if (isNaN(d.getTime())) return dateStr;
      const months = [
        'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
        'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'
      ];
      return `${d.getDate()} ${months[d.getMonth()]} ${d.getFullYear()}`;
    } catch (e) {
      return dateStr;
    }
  },

  /**
   * Parses query parameter from current window URL.
   * @param {string} name 
   * @returns {string|null}
   */
  getQueryParam(name) {
    const params = new URLSearchParams(window.location.search);
    return params.get(name);
  },

  /**
   * Displays non-blocking toast feedback alert.
   * @param {string} message 
   * @param {string} type 'success' | 'error' | 'warning'
   */
  showToast(message, type = 'success') {
    let container = document.getElementById('toastContainer');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toastContainer';
      container.className = 'toast-container';
      document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    const icon = type === 'success' ? '✓' : (type === 'error' ? '✕' : '⚠');
    toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;

    container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 3800);
  }
};
