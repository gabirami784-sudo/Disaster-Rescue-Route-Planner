-- ======================================================
-- Disaster Rescue Route Planner - Database Schema & Data
-- Database Name: disaster_rescue_db
-- ======================================================

CREATE DATABASE IF NOT EXISTS `disaster_rescue_db` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `disaster_rescue_db`;

-- Drop existing tables if they exist (in reverse FK dependency order)
DROP TABLE IF EXISTS `emergencies`;
DROP TABLE IF EXISTS `roads`;
DROP TABLE IF EXISTS `locations`;
DROP TABLE IF EXISTS `users`;

-- 1. Table: users
CREATE TABLE `users` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `username` VARCHAR(50) NOT NULL UNIQUE,
    `password` VARCHAR(255) NOT NULL,
    `role` ENUM('Admin', 'Rescue Team') NOT NULL DEFAULT 'Rescue Team',
    `full_name` VARCHAR(100) NOT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. Table: locations
CREATE TABLE `locations` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(100) NOT NULL UNIQUE,
    `type` ENUM('Disaster Area', 'Rescue Center', 'Hospital', 'Safe Zone') NOT NULL,
    `latitude` DECIMAL(10, 6) NOT NULL DEFAULT 0.000000,
    `longitude` DECIMAL(10, 6) NOT NULL DEFAULT 0.000000,
    `emergency_level` ENUM('None', 'Low', 'Medium', 'High', 'Critical') NOT NULL DEFAULT 'None',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. Table: roads (Graph Edges)
CREATE TABLE `roads` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `source_id` INT NOT NULL,
    `destination_id` INT NOT NULL,
    `distance` DECIMAL(8, 2) NOT NULL COMMENT 'Distance in kilometers',
    `status` ENUM('Open', 'Blocked') NOT NULL DEFAULT 'Open',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`source_id`) REFERENCES `locations`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`destination_id`) REFERENCES `locations`(`id`) ON DELETE CASCADE,
    CONSTRAINT `unique_road_pair` UNIQUE (`source_id`, `destination_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. Table: emergencies
CREATE TABLE `emergencies` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `location_id` INT NOT NULL,
    `people_affected` INT NOT NULL DEFAULT 1,
    `emergency_level` ENUM('Critical', 'High', 'Medium', 'Low') NOT NULL DEFAULT 'Medium',
    `destination_id` INT DEFAULT NULL,
    `description` TEXT,
    `status` ENUM('Pending', 'In Progress', 'Resolved') NOT NULL DEFAULT 'Pending',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`location_id`) REFERENCES `locations`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`destination_id`) REFERENCES `locations`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ======================================================
-- SAMPLE SEED DATA
-- ======================================================

-- Passwords below are plain/hashed. App supports both plain and hashed matching.
-- Admin user: admin / admin123
-- Rescue Team user: rescuer / user123
INSERT INTO `users` (`username`, `password`, `role`, `full_name`) VALUES
('admin', 'pbkdf2:sha256:600000$c36N18kY$8d9fa89e4726b2b7ec17cfb2d184719c63283287042be64d9435b6fb89b02a9b', 'Admin', 'Head Commander Admin'),
('rescuer', 'pbkdf2:sha256:600000$c36N18kY$8d9fa89e4726b2b7ec17cfb2d184719c63283287042be64d9435b6fb89b02a9b', 'Rescue Team', 'Rescue Team Alpha');

-- Insert Sample Locations
INSERT INTO `locations` (`id`, `name`, `type`, `latitude`, `longitude`, `emergency_level`) VALUES
(1, 'Flood Area A', 'Disaster Area', 12.971598, 77.594566, 'Critical'),
(2, 'Junction A', 'Safe Zone', 12.973000, 77.598000, 'None'),
(3, 'Rescue Center A', 'Rescue Center', 12.975000, 77.600000, 'None'),
(4, 'Junction B', 'Safe Zone', 12.978000, 77.605000, 'None'),
(5, 'Hospital A', 'Hospital', 12.980000, 77.610000, 'None'),
(6, 'Safe Zone A', 'Safe Zone', 12.965000, 77.590000, 'None'),
(7, 'Landslide Area B', 'Disaster Area', 12.960000, 77.580000, 'High'),
(8, 'Hospital B', 'Hospital', 12.955000, 77.575000, 'None');

-- Insert Sample Roads (Graph Connections)
-- Note: Junction A to Junction B is set to 'Blocked' to demonstrate algorithm bypassing blocked roads
INSERT INTO `roads` (`source_id`, `destination_id`, `distance`, `status`) VALUES
(1, 2, 2.50, 'Open'),      -- Flood Area A <-> Junction A
(2, 4, 3.00, 'Blocked'),   -- Junction A <-> Junction B (BLOCKED ROAD)
(2, 3, 4.00, 'Open'),      -- Junction A <-> Rescue Center A
(3, 4, 2.00, 'Open'),      -- Rescue Center A <-> Junction B
(4, 5, 3.50, 'Open'),      -- Junction B <-> Hospital A
(1, 6, 5.00, 'Open'),      -- Flood Area A <-> Safe Zone A
(6, 8, 4.20, 'Open'),      -- Safe Zone A <-> Hospital B
(7, 8, 1.80, 'Open');      -- Landslide Area B <-> Hospital B

-- Insert Sample Emergencies
INSERT INTO `emergencies` (`location_id`, `people_affected`, `emergency_level`, `destination_id`, `description`, `status`) VALUES
(1, 45, 'Critical', 5, 'Flash flood trapping 45 residents on roof tops. Immediate evacuation required.', 'Pending'),
(7, 20, 'High', 8, 'Landslide blocking residential access. 20 citizens need medical checkup.', 'Pending'),
(6, 12, 'Medium', 3, 'Temporary shelter requesting extra food and medical supply kits.', 'In Progress'),
(1, 5, 'Low', 5, 'Minor injuries reported during water drainage operations.', 'Pending');
