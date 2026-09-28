-- ========================================================
-- Healthcare Appointment Agent System - MySQL Schema DDL
-- Database Version: MySQL 8.0+
-- ========================================================

CREATE DATABASE IF NOT EXISTS `healthcare_db` 
CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE `healthcare_db`;

SET FOREIGN_KEY_CHECKS = 0;

-- --------------------------------------------------------
-- Table: roles
-- --------------------------------------------------------
DROP TABLE IF EXISTS `roles`;
CREATE TABLE `roles` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(50) NOT NULL UNIQUE,
    `description` VARCHAR(255) NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_roles_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- Table: users
-- --------------------------------------------------------
DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `email` VARCHAR(120) NOT NULL UNIQUE,
    `password_hash` VARCHAR(255) NOT NULL,
    `role_id` INT NOT NULL,
    `full_name` VARCHAR(100) NOT NULL,
    `phone` VARCHAR(20) NULL,
    `is_active` BOOLEAN NOT NULL DEFAULT TRUE,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_users_email` (`email`),
    INDEX `idx_users_role_id` (`role_id`),
    CONSTRAINT `fk_users_role` FOREIGN KEY (`role_id`) REFERENCES `roles` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- Table: specializations
-- --------------------------------------------------------
DROP TABLE IF EXISTS `specializations`;
CREATE TABLE `specializations` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(80) NOT NULL UNIQUE,
    `description` TEXT NULL,
    `icon` VARCHAR(50) DEFAULT 'medical_services',
    `keywords` TEXT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_specializations_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- Table: patients
-- --------------------------------------------------------
DROP TABLE IF EXISTS `patients`;
CREATE TABLE `patients` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL UNIQUE,
    `date_of_birth` DATE NULL,
    `gender` VARCHAR(20) NULL,
    `blood_group` VARCHAR(10) NULL,
    `address` TEXT NULL,
    `emergency_contact` VARCHAR(50) NULL,
    `medical_history` TEXT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_patients_user_id` (`user_id`),
    CONSTRAINT `fk_patients_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- Table: doctors
-- --------------------------------------------------------
DROP TABLE IF EXISTS `doctors`;
CREATE TABLE `doctors` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL UNIQUE,
    `specialization_id` INT NOT NULL,
    `qualification` VARCHAR(100) NOT NULL,
    `experience_years` INT NOT NULL DEFAULT 5,
    `rating` DECIMAL(3,2) NOT NULL DEFAULT 4.80,
    `consultation_fee` DECIMAL(10,2) NOT NULL DEFAULT 50.00,
    `bio` TEXT NULL,
    `room_number` VARCHAR(30) NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_doctors_user_id` (`user_id`),
    INDEX `idx_doctors_specialization_id` (`specialization_id`),
    INDEX `idx_doctors_rating` (`rating`),
    CONSTRAINT `fk_doctors_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_doctors_specialization` FOREIGN KEY (`specialization_id`) REFERENCES `specializations` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- Table: doctor_availability
-- --------------------------------------------------------
DROP TABLE IF EXISTS `doctor_availability`;
CREATE TABLE `doctor_availability` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `doctor_id` INT NOT NULL,
    `day_of_week` TINYINT NOT NULL COMMENT '0=Monday, 6=Sunday',
    `start_time` TIME NOT NULL,
    `end_time` TIME NOT NULL,
    `slot_duration_minutes` INT NOT NULL DEFAULT 30,
    `is_active` BOOLEAN NOT NULL DEFAULT TRUE,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_doc_avail_doctor` (`doctor_id`),
    INDEX `idx_doc_avail_day` (`day_of_week`),
    CONSTRAINT `fk_avail_doctor` FOREIGN KEY (`doctor_id`) REFERENCES `doctors` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- Table: appointments
-- --------------------------------------------------------
DROP TABLE IF EXISTS `appointments`;
CREATE TABLE `appointments` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `patient_id` INT NOT NULL,
    `doctor_id` INT NOT NULL,
    `appointment_date` DATE NOT NULL,
    `start_time` TIME NOT NULL,
    `end_time` TIME NOT NULL,
    `status` ENUM('pending', 'confirmed', 'completed', 'cancelled', 'rescheduled') NOT NULL DEFAULT 'confirmed',
    `chief_complaint` TEXT NULL,
    `booking_source` VARCHAR(20) NOT NULL DEFAULT 'agent_auto',
    `cancellation_reason` TEXT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_appts_patient` (`patient_id`),
    INDEX `idx_appts_doctor` (`doctor_id`),
    INDEX `idx_appts_date` (`appointment_date`),
    INDEX `idx_appts_status` (`status`),
    CONSTRAINT `fk_appts_patient` FOREIGN KEY (`patient_id`) REFERENCES `patients` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_appts_doctor` FOREIGN KEY (`doctor_id`) REFERENCES `doctors` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- Table: symptoms
-- --------------------------------------------------------
DROP TABLE IF EXISTS `symptoms`;
CREATE TABLE `symptoms` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `patient_id` INT NULL,
    `raw_text` TEXT NOT NULL,
    `detected_specialization_id` INT NULL,
    `confidence_score` DECIMAL(4,3) NOT NULL DEFAULT 0.000,
    `urgency_level` ENUM('low', 'medium', 'high', 'emergency') NOT NULL DEFAULT 'medium',
    `extracted_keywords` TEXT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_symptoms_patient` (`patient_id`),
    INDEX `idx_symptoms_detected_spec` (`detected_specialization_id`),
    CONSTRAINT `fk_symptoms_patient` FOREIGN KEY (`patient_id`) REFERENCES `patients` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_symptoms_spec` FOREIGN KEY (`detected_specialization_id`) REFERENCES `specializations` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- Table: agent_decisions
-- --------------------------------------------------------
DROP TABLE IF EXISTS `agent_decisions`;
CREATE TABLE `agent_decisions` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `symptom_id` INT NOT NULL,
    `recommended_doctor_id` INT NOT NULL,
    `recommended_slot` VARCHAR(100) NOT NULL,
    `decision_score` DECIMAL(5,4) NOT NULL DEFAULT 0.0000,
    `score_breakdown` JSON NULL,
    `decision_reason` TEXT NOT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_decisions_symptom` (`symptom_id`),
    INDEX `idx_decisions_doctor` (`recommended_doctor_id`),
    CONSTRAINT `fk_decisions_symptom` FOREIGN KEY (`symptom_id`) REFERENCES `symptoms` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_decisions_doctor` FOREIGN KEY (`recommended_doctor_id`) REFERENCES `doctors` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- Table: notifications
-- --------------------------------------------------------
DROP TABLE IF EXISTS `notifications`;
CREATE TABLE `notifications` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `appointment_id` INT NULL,
    `type` VARCHAR(50) NOT NULL,
    `channel` VARCHAR(20) NOT NULL DEFAULT 'email',
    `recipient` VARCHAR(120) NOT NULL,
    `subject` VARCHAR(255) NOT NULL,
    `message` TEXT NOT NULL,
    `status` VARCHAR(20) NOT NULL DEFAULT 'sent',
    `sent_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_notifs_user` (`user_id`),
    INDEX `idx_notifs_appt` (`appointment_id`),
    CONSTRAINT `fk_notifs_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_notifs_appt` FOREIGN KEY (`appointment_id`) REFERENCES `appointments` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- Table: medical_notes
-- --------------------------------------------------------
DROP TABLE IF EXISTS `medical_notes`;
CREATE TABLE `medical_notes` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `appointment_id` INT NOT NULL UNIQUE,
    `doctor_id` INT NOT NULL,
    `diagnosis` TEXT NOT NULL,
    `prescription` TEXT NULL,
    `clinical_notes` TEXT NULL,
    `follow_up_date` DATE NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_notes_appt` (`appointment_id`),
    INDEX `idx_notes_doctor` (`doctor_id`),
    CONSTRAINT `fk_notes_appt` FOREIGN KEY (`appointment_id`) REFERENCES `appointments` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_notes_doctor` FOREIGN KEY (`doctor_id`) REFERENCES `doctors` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;
