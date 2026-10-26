/**
 * DonasiKita - API Client Bridge
 * Asynchronously interfaces with Python Eel exposed backend functions.
 */

const API = {
  /**
   * Helper to execute Eel backend function with Promise support.
   */
  async callEel(funcName, ...args) {
    if (typeof eel !== 'undefined' && typeof eel[funcName] === 'function') {
      try {
        return await eel[funcName](...args)();
      } catch (err) {
        console.error(`Eel execution error in ${funcName}:`, err);
        return { success: false, message: `Kesalahan backend: ${err.message || err}` };
      }
    } else {
      console.warn(`Eel bridge function '${funcName}' is not available yet.`);
      return { success: false, message: "Koneksi backend Eel belum siap. Pastikan aplikasi dijalankan via Python." };
    }
  },

  // --------------------------------------------------------------------------
  // Auth & User Management
  // --------------------------------------------------------------------------
  login(email, password) {
    return this.callEel('py_login', email, password);
  },

  register(fullName, email, password, role, phone) {
    return this.callEel('py_register', fullName, email, password, role, phone);
  },

  logout(sessionToken) {
    return this.callEel('py_logout', sessionToken);
  },

  getCurrentUser(sessionToken) {
    return this.callEel('py_get_current_user_profile', sessionToken);
  },

  getAllUsers(sessionToken) {
    return this.callEel('py_get_all_users', sessionToken);
  },

  updateUserStatus(sessionToken, targetUserId, newStatus) {
    return this.callEel('py_update_user_status', sessionToken, targetUserId, newStatus);
  },

  // --------------------------------------------------------------------------
  // Public & Campaigns
  // --------------------------------------------------------------------------
  getLandingPageData() {
    return this.callEel('py_get_landing_page_data');
  },

  getCategories() {
    return this.callEel('py_get_categories');
  },

  getCampaigns(categorySlug, searchKeyword, status, sortBy) {
    return this.callEel('py_get_campaigns', categorySlug, searchKeyword, status, sortBy);
  },

  getCampaignDetail(slugOrId) {
    return this.callEel('py_get_campaign_detail', slugOrId);
  },

  // --------------------------------------------------------------------------
  // Fundraiser Management
  // --------------------------------------------------------------------------
  createCampaign(sessionToken, title, categoryId, targetAmount, deadlineDate, shortDesc, story, imageUrl) {
    return this.callEel('py_create_campaign', sessionToken, title, categoryId, targetAmount, deadlineDate, shortDesc, story, imageUrl);
  },

  getFundraiserCampaigns(sessionToken) {
    return this.callEel('py_get_fundraiser_campaigns', sessionToken);
  },

  updateCampaign(sessionToken, campaignId, title, categoryId, targetAmount, deadlineDate, shortDesc, story, imageUrl) {
    return this.callEel('py_update_campaign', sessionToken, campaignId, title, categoryId, targetAmount, deadlineDate, shortDesc, story, imageUrl);
  },

  deleteCampaign(sessionToken, campaignId) {
    return this.callEel('py_delete_campaign', sessionToken, campaignId);
  },

  addCampaignUpdate(sessionToken, campaignId, title, content, imageUrl) {
    return this.callEel('py_add_campaign_update', sessionToken, campaignId, title, content, imageUrl);
  },

  addFundUsageReport(sessionToken, campaignId, expenseTitle, expenseCategory, amount, expenseDate, description, proofDoc) {
    return this.callEel('py_add_fund_usage_report', sessionToken, campaignId, expenseTitle, expenseCategory, amount, expenseDate, description, proofDoc);
  },

  getFundraiserDashboardSummary(sessionToken) {
    return this.callEel('py_get_fundraiser_dashboard_summary', sessionToken);
  },

  // --------------------------------------------------------------------------
  // Donations & Payments
  // --------------------------------------------------------------------------
  createDonation(sessionToken, campaignId, amount, isAnonymous, prayerMessage, paymentMethod, paymentChannel) {
    return this.callEel('py_create_donation', sessionToken, campaignId, amount, isAnonymous, prayerMessage, paymentMethod, paymentChannel);
  },

  getDonationByCode(donationCode) {
    return this.callEel('py_get_donation_by_code', donationCode);
  },

  simulatePayment(paymentCode, action) {
    return this.callEel('py_simulate_payment', paymentCode, action);
  },

  getUserDonations(sessionToken) {
    return this.callEel('py_get_user_donations', sessionToken);
  },

  // --------------------------------------------------------------------------
  // Digital Certificate
  // --------------------------------------------------------------------------
  getCertificateDetail(certificateNumber) {
    return this.callEel('py_get_certificate_detail', certificateNumber);
  },

  getCertificateByDonationCode(donationCode) {
    return this.callEel('py_get_certificate_by_donation_code', donationCode);
  },

  // --------------------------------------------------------------------------
  // Admin Operations
  // --------------------------------------------------------------------------
  getAdminDashboardSummary(sessionToken) {
    return this.callEel('py_get_admin_dashboard_summary', sessionToken);
  },

  getAllCampaignsAdmin(sessionToken, statusFilter) {
    return this.callEel('py_get_all_campaigns_admin', sessionToken, statusFilter);
  },

  approveCampaign(sessionToken, campaignId) {
    return this.callEel('py_approve_campaign', sessionToken, campaignId);
  },

  rejectCampaign(sessionToken, campaignId, reason) {
    return this.callEel('py_reject_campaign', sessionToken, campaignId, reason);
  },

  completeCampaign(sessionToken, campaignId) {
    return this.callEel('py_complete_campaign', sessionToken, campaignId);
  },

  getAllDonationsAdmin(sessionToken, statusFilter) {
    return this.callEel('py_get_all_donations_admin', sessionToken, statusFilter);
  },

  exportDonationsCSV(sessionToken, campaignId) {
    return this.callEel('py_export_donations_csv', sessionToken, campaignId);
  }
};
