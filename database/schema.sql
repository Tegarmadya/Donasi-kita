-- ==============================================================================
-- DonasiKita Database Schema
-- Platform E-Donation & E-Crowdfunding
-- Engine: InnoDB | Charset: utf8mb4 | Collation: utf8mb4_unicode_ci
-- ==============================================================================

-- Nonaktifkan foreign key checks selama pembuatan skema
SET FOREIGN_KEY_CHECKS = 0;

-- ------------------------------------------------------------------------------
-- 1. Table: users
-- Menyimpan identitas pengguna dengan peran admin, fundraiser (penggalang dana), donatur
-- ------------------------------------------------------------------------------
DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `full_name` VARCHAR(120) NOT NULL,
    `email` VARCHAR(150) NOT NULL UNIQUE,
    `password_hash` VARCHAR(255) NOT NULL,
    `role` ENUM('admin', 'fundraiser', 'donatur') NOT NULL DEFAULT 'donatur',
    `phone` VARCHAR(20) DEFAULT NULL,
    `avatar` VARCHAR(255) DEFAULT 'default_avatar.png',
    `status` ENUM('active', 'suspended') NOT NULL DEFAULT 'active',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_users_role` (`role`),
    INDEX `idx_users_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------------------------
-- 2. Table: categories
-- Kategori campaign (contoh: Medis & Kesehatan, Bencana Alam, Pendidikan, dll)
-- ------------------------------------------------------------------------------
DROP TABLE IF EXISTS `categories`;
CREATE TABLE `categories` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(80) NOT NULL,
    `slug` VARCHAR(100) NOT NULL UNIQUE,
    `description` VARCHAR(255) DEFAULT NULL,
    `icon` VARCHAR(50) DEFAULT 'heart',
    `is_active` TINYINT(1) NOT NULL DEFAULT 1,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------------------------
-- 3. Table: campaigns
-- Data program penggalangan dana yang dibuat oleh fundraiser
-- Status: draft, pending (menunggu verifikasi admin), active, rejected, completed
-- ------------------------------------------------------------------------------
DROP TABLE IF EXISTS `campaigns`;
CREATE TABLE `campaigns` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `category_id` INT NOT NULL,
    `title` VARCHAR(200) NOT NULL,
    `slug` VARCHAR(220) NOT NULL UNIQUE,
    `short_description` VARCHAR(300) NOT NULL,
    `story` LONGTEXT NOT NULL,
    `target_amount` DECIMAL(15,2) NOT NULL DEFAULT 0.00,
    `collected_amount` DECIMAL(15,2) NOT NULL DEFAULT 0.00,
    `deadline_date` DATE NOT NULL,
    `image_url` VARCHAR(255) NOT NULL,
    `status` ENUM('draft', 'pending', 'active', 'rejected', 'completed') NOT NULL DEFAULT 'pending',
    `rejection_reason` TEXT DEFAULT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_campaigns_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_campaigns_category` FOREIGN KEY (`category_id`) REFERENCES `categories` (`id`) ON DELETE RESTRICT,
    INDEX `idx_campaigns_status` (`status`),
    INDEX `idx_campaigns_category` (`category_id`),
    INDEX `idx_campaigns_deadline` (`deadline_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------------------------
-- 4. Table: donations
-- Catatan transaksi donasi elektronik
-- Status: pending, success, failed, expired
-- ------------------------------------------------------------------------------
DROP TABLE IF EXISTS `donations`;
CREATE TABLE `donations` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `donation_code` VARCHAR(50) NOT NULL UNIQUE,
    `campaign_id` INT NOT NULL,
    `user_id` INT DEFAULT NULL,
    `donor_name` VARCHAR(120) NOT NULL,
    `donor_email` VARCHAR(150) NOT NULL,
    `amount` DECIMAL(15,2) NOT NULL,
    `is_anonymous` TINYINT(1) NOT NULL DEFAULT 0,
    `prayer_message` TEXT DEFAULT NULL,
    `status` ENUM('pending', 'success', 'failed', 'expired') NOT NULL DEFAULT 'pending',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_donations_campaign` FOREIGN KEY (`campaign_id`) REFERENCES `campaigns` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_donations_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL,
    INDEX `idx_donations_campaign` (`campaign_id`),
    INDEX `idx_donations_status` (`status`),
    INDEX `idx_donations_user` (`user_id`),
    INDEX `idx_donations_created` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------------------------
-- 5. Table: payments
-- Detail informasi pembayaran simulasi elektronik
-- ------------------------------------------------------------------------------
DROP TABLE IF EXISTS `payments`;
CREATE TABLE `payments` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `payment_code` VARCHAR(50) NOT NULL UNIQUE,
    `donation_id` INT NOT NULL UNIQUE,
    `payment_method` ENUM('bank_transfer', 'qris', 'ewallet') NOT NULL,
    `payment_channel` VARCHAR(50) NOT NULL,
    `payment_status` ENUM('pending', 'success', 'failed') NOT NULL DEFAULT 'pending',
    `payment_reference` VARCHAR(100) DEFAULT NULL,
    `instructions` TEXT DEFAULT NULL,
    `paid_at` TIMESTAMP NULL DEFAULT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_payments_donation` FOREIGN KEY (`donation_id`) REFERENCES `donations` (`id`) ON DELETE CASCADE,
    INDEX `idx_payments_status` (`payment_status`),
    INDEX `idx_payments_method` (`payment_method`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------------------------
-- 6. Table: campaign_updates
-- Kabar terbaru / perkembangan kondisi penerima donasi yang diposting penggalang dana
-- ------------------------------------------------------------------------------
DROP TABLE IF EXISTS `campaign_updates`;
CREATE TABLE `campaign_updates` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `campaign_id` INT NOT NULL,
    `title` VARCHAR(200) NOT NULL,
    `content` LONGTEXT NOT NULL,
    `image_url` VARCHAR(255) DEFAULT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_updates_campaign` FOREIGN KEY (`campaign_id`) REFERENCES `campaigns` (`id`) ON DELETE CASCADE,
    INDEX `idx_updates_campaign` (`campaign_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------------------------
-- 7. Table: fund_usage_reports
-- Transparansi pengeluaran & pencairan dana yang dilaporkan oleh penggalang dana
-- ------------------------------------------------------------------------------
DROP TABLE IF EXISTS `fund_usage_reports`;
CREATE TABLE `fund_usage_reports` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `campaign_id` INT NOT NULL,
    `expense_title` VARCHAR(200) NOT NULL,
    `expense_category` VARCHAR(100) NOT NULL,
    `amount` DECIMAL(15,2) NOT NULL,
    `expense_date` DATE NOT NULL,
    `description` TEXT NOT NULL,
    `proof_document` VARCHAR(255) DEFAULT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_fund_usage_campaign` FOREIGN KEY (`campaign_id`) REFERENCES `campaigns` (`id`) ON DELETE CASCADE,
    INDEX `idx_fund_usage_campaign` (`campaign_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------------------------
-- 8. Table: certificates
-- Sertifikat donasi digital resmi yang diterbitkan hanya untuk donasi sukses
-- ------------------------------------------------------------------------------
DROP TABLE IF EXISTS `certificates`;
CREATE TABLE `certificates` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `certificate_number` VARCHAR(60) NOT NULL UNIQUE,
    `donation_id` INT NOT NULL UNIQUE,
    `donor_name_display` VARCHAR(120) NOT NULL,
    `campaign_title` VARCHAR(200) NOT NULL,
    `amount` DECIMAL(15,2) NOT NULL,
    `issue_date` DATE NOT NULL,
    `verification_code` VARCHAR(64) NOT NULL UNIQUE,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_certificates_donation` FOREIGN KEY (`donation_id`) REFERENCES `donations` (`id`) ON DELETE CASCADE,
    INDEX `idx_certificates_number` (`certificate_number`),
    INDEX `idx_certificates_verification` (`verification_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Kembalikan foreign key checks
SET FOREIGN_KEY_CHECKS = 1;
