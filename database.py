"""
DATABASE LAYER MODULE
=====================
Provides clean CRUD interface and database connectivity for Disaster Rescue Route Planner.
Supports MySQL database (primary) with automatic SQLite fallback if MySQL server is offline or inaccessible.
Uses parameterized queries to prevent SQL injection and returns dictionary records.
"""

import os
import sqlite3
import pymysql
import pymysql.cursors
from werkzeug.security import check_password_hash, generate_password_hash
from config import Config

# Flag tracking active database driver ('mysql' or 'sqlite')
DB_DRIVER = 'mysql'
SQLITE_DB_PATH = os.path.join(os.path.dirname(__file__), 'disaster_rescue.db')


class SQLiteDictCursor:
    """Helper wrapper for sqlite3 connection to act like pymysql DictCursor."""
    def __init__(self, conn):
        self.conn = conn
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.lastrowid = None
        self.rowcount = 0

    def execute(self, query, params=()):
        # Convert MySQL %s placeholders to SQLite ? placeholders
        sqlite_query = query.replace('%s', '?')
        self.cursor.execute(sqlite_query, params)
        self.lastrowid = self.cursor.lastrowid
        self.rowcount = self.cursor.rowcount
        return self

    def fetchone(self):
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def fetchall(self):
        rows = self.cursor.fetchall()
        return [dict(r) for r in rows]

    def close(self):
        self.cursor.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.conn.commit()
        self.close()


def get_db():
    """
    Returns database connection / context manager wrapper compatible with both MySQL and SQLite.
    """
    global DB_DRIVER
    if DB_DRIVER == 'sqlite':
        conn = sqlite3.connect(SQLITE_DB_PATH)
        return SQLiteDictCursor(conn)

    try:
        conn = pymysql.connect(
            host=Config.MYSQL_HOST,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DB,
            port=Config.MYSQL_PORT,
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True
        )
        return conn.cursor()
    except Exception:
        # Fallback to SQLite if MySQL connection fails
        DB_DRIVER = 'sqlite'
        conn = sqlite3.connect(SQLITE_DB_PATH)
        return SQLiteDictCursor(conn)


def init_db():
    """
    Initializes database schema.
    Attempts MySQL connection first; falls back seamlessly to SQLite if MySQL is unavailable.
    """
    global DB_DRIVER
    try:
        # Attempt MySQL setup
        conn = pymysql.connect(
            host=Config.MYSQL_HOST,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            port=Config.MYSQL_PORT,
            autocommit=True
        )
        with conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{Config.MYSQL_DB}` DEFAULT CHARACTER SET utf8mb4;")
        conn.close()

        # Connect to MySQL DB and verify tables
        conn_db = pymysql.connect(
            host=Config.MYSQL_HOST,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DB,
            port=Config.MYSQL_PORT,
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True
        )
        with conn_db.cursor() as cursor:
            cursor.execute("SHOW TABLES LIKE 'users';")
            if not cursor.fetchone():
                _execute_mysql_schema(cursor)
        conn_db.close()
        DB_DRIVER = 'mysql'
        print(f"[Database] Successfully connected to MySQL database '{Config.MYSQL_DB}'.")
        return True, "MySQL Database initialized."

    except Exception as mysql_err:
        print(f"[Database Warning] MySQL connection unavailable ({mysql_err}). Initializing SQLite fallback...")
        DB_DRIVER = 'sqlite'
        _init_sqlite_db()
        return True, "SQLite fallback initialized."


def _execute_mysql_schema(cursor):
    """Executes MySQL DDL schema and sample seed data."""
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS `users` (
        `id` INT AUTO_INCREMENT PRIMARY KEY,
        `username` VARCHAR(50) NOT NULL UNIQUE,
        `password` VARCHAR(255) NOT NULL,
        `role` ENUM('Admin', 'Rescue Team') NOT NULL DEFAULT 'Rescue Team',
        `full_name` VARCHAR(100) NOT NULL,
        `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS `locations` (
        `id` INT AUTO_INCREMENT PRIMARY KEY,
        `name` VARCHAR(100) NOT NULL UNIQUE,
        `type` ENUM('Disaster Area', 'Rescue Center', 'Hospital', 'Safe Zone') NOT NULL,
        `latitude` DECIMAL(10, 6) NOT NULL DEFAULT 0.000000,
        `longitude` DECIMAL(10, 6) NOT NULL DEFAULT 0.000000,
        `emergency_level` ENUM('None', 'Low', 'Medium', 'High', 'Critical') NOT NULL DEFAULT 'None',
        `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS `roads` (
        `id` INT AUTO_INCREMENT PRIMARY KEY,
        `source_id` INT NOT NULL,
        `destination_id` INT NOT NULL,
        `distance` DECIMAL(8, 2) NOT NULL,
        `status` ENUM('Open', 'Blocked') NOT NULL DEFAULT 'Open',
        `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (`source_id`) REFERENCES `locations`(`id`) ON DELETE CASCADE,
        FOREIGN KEY (`destination_id`) REFERENCES `locations`(`id`) ON DELETE CASCADE,
        CONSTRAINT `unique_road_pair` UNIQUE (`source_id`, `destination_id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS `emergencies` (
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
    """)

    _insert_seed_data(cursor)


def _init_sqlite_db():
    """Initializes SQLite database schema and seed records."""
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'Rescue Team',
        full_name TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS locations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        type TEXT NOT NULL,
        latitude REAL NOT NULL DEFAULT 0.0,
        longitude REAL NOT NULL DEFAULT 0.0,
        emergency_level TEXT NOT NULL DEFAULT 'None',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS roads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_id INTEGER NOT NULL,
        destination_id INTEGER NOT NULL,
        distance REAL NOT NULL,
        status TEXT NOT NULL DEFAULT 'Open',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (source_id) REFERENCES locations(id) ON DELETE CASCADE,
        FOREIGN KEY (destination_id) REFERENCES locations(id) ON DELETE CASCADE,
        UNIQUE (source_id, destination_id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS emergencies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        location_id INTEGER NOT NULL,
        people_affected INTEGER NOT NULL DEFAULT 1,
        emergency_level TEXT NOT NULL DEFAULT 'Medium',
        destination_id INTEGER DEFAULT NULL,
        description TEXT,
        status TEXT NOT NULL DEFAULT 'Pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE CASCADE,
        FOREIGN KEY (destination_id) REFERENCES locations(id) ON DELETE SET NULL
    );
    """)

    # Check if seed data exists
    cursor.execute("SELECT COUNT(*) FROM users;")
    if cursor.fetchone()[0] == 0:
        pass_hash = generate_password_hash("admin123")
        user_hash = generate_password_hash("user123")

        cursor.execute("INSERT INTO users (username, password, role, full_name) VALUES (?, ?, ?, ?)",
                       ('admin', pass_hash, 'Admin', 'Head Commander Admin'))
        cursor.execute("INSERT INTO users (username, password, role, full_name) VALUES (?, ?, ?, ?)",
                       ('rescuer', user_hash, 'Rescue Team', 'Rescue Team Alpha'))

        locations_seed = [
            ('Flood Area A', 'Disaster Area', 12.971598, 77.594566, 'Critical'),
            ('Junction A', 'Safe Zone', 12.973000, 77.598000, 'None'),
            ('Rescue Center A', 'Rescue Center', 12.975000, 77.600000, 'None'),
            ('Junction B', 'Safe Zone', 12.978000, 77.605000, 'None'),
            ('Hospital A', 'Hospital', 12.980000, 77.610000, 'None'),
            ('Safe Zone A', 'Safe Zone', 12.965000, 77.590000, 'None'),
            ('Landslide Area B', 'Disaster Area', 12.960000, 77.580000, 'High'),
            ('Hospital B', 'Hospital', 12.955000, 77.575000, 'None')
        ]
        for loc in locations_seed:
            cursor.execute("INSERT INTO locations (name, type, latitude, longitude, emergency_level) VALUES (?, ?, ?, ?, ?)", loc)

        roads_seed = [
            (1, 2, 2.50, 'Open'),
            (2, 4, 3.00, 'Blocked'),
            (2, 3, 4.00, 'Open'),
            (3, 4, 2.00, 'Open'),
            (4, 5, 3.50, 'Open'),
            (1, 6, 5.00, 'Open'),
            (6, 8, 4.20, 'Open'),
            (7, 8, 1.80, 'Open')
        ]
        for road in roads_seed:
            cursor.execute("INSERT INTO roads (source_id, destination_id, distance, status) VALUES (?, ?, ?, ?)", road)

        emergencies_seed = [
            (1, 45, 'Critical', 5, 'Flash flood trapping 45 residents on roof tops. Immediate evacuation required.', 'Pending'),
            (7, 20, 'High', 8, 'Landslide blocking residential access. 20 citizens need medical checkup.', 'Pending'),
            (6, 12, 'Medium', 3, 'Temporary shelter requesting extra food and medical supply kits.', 'In Progress'),
            (1, 5, 'Low', 5, 'Minor injuries reported during water drainage operations.', 'Pending')
        ]
        for em in emergencies_seed:
            cursor.execute("INSERT INTO emergencies (location_id, people_affected, emergency_level, destination_id, description, status) VALUES (?, ?, ?, ?, ?, ?)", em)

    conn.commit()
    conn.close()


def _insert_seed_data(cursor):
    """Inserts seed data into MySQL."""
    pass_hash = generate_password_hash("admin123")
    user_hash = generate_password_hash("user123")

    cursor.execute("INSERT INTO `users` (`username`, `password`, `role`, `full_name`) VALUES (%s, %s, %s, %s)",
                   ('admin', pass_hash, 'Admin', 'Head Commander Admin'))
    cursor.execute("INSERT INTO `users` (`username`, `password`, `role`, `full_name`) VALUES (%s, %s, %s, %s)",
                   ('rescuer', user_hash, 'Rescue Team', 'Rescue Team Alpha'))

    locations_seed = [
        ('Flood Area A', 'Disaster Area', 12.971598, 77.594566, 'Critical'),
        ('Junction A', 'Safe Zone', 12.973000, 77.598000, 'None'),
        ('Rescue Center A', 'Rescue Center', 12.975000, 77.600000, 'None'),
        ('Junction B', 'Safe Zone', 12.978000, 77.605000, 'None'),
        ('Hospital A', 'Hospital', 12.980000, 77.610000, 'None'),
        ('Safe Zone A', 'Safe Zone', 12.965000, 77.590000, 'None'),
        ('Landslide Area B', 'Disaster Area', 12.960000, 77.580000, 'High'),
        ('Hospital B', 'Hospital', 12.955000, 77.575000, 'None')
    ]
    for loc in locations_seed:
        cursor.execute("INSERT INTO `locations` (`name`, `type`, `latitude`, `longitude`, `emergency_level`) VALUES (%s, %s, %s, %s, %s)", loc)

    roads_seed = [
        (1, 2, 2.50, 'Open'),
        (2, 4, 3.00, 'Blocked'),
        (2, 3, 4.00, 'Open'),
        (3, 4, 2.00, 'Open'),
        (4, 5, 3.50, 'Open'),
        (1, 6, 5.00, 'Open'),
        (6, 8, 4.20, 'Open'),
        (7, 8, 1.80, 'Open')
    ]
    for road in roads_seed:
        cursor.execute("INSERT INTO `roads` (`source_id`, `destination_id`, `distance`, `status`) VALUES (%s, %s, %s, %s)", road)

    emergencies_seed = [
        (1, 45, 'Critical', 5, 'Flash flood trapping 45 residents on roof tops. Immediate evacuation required.', 'Pending'),
        (7, 20, 'High', 8, 'Landslide blocking residential access. 20 citizens need medical checkup.', 'Pending'),
        (6, 12, 'Medium', 3, 'Temporary shelter requesting extra food and medical supply kits.', 'In Progress'),
        (1, 5, 'Low', 5, 'Minor injuries reported during water drainage operations.', 'Pending')
    ]
    for em in emergencies_seed:
        cursor.execute("INSERT INTO `emergencies` (`location_id`, `people_affected`, `emergency_level`, `destination_id`, `description`, `status`) VALUES (%s, %s, %s, %s, %s, %s)", em)


# ==========================================
# USER MANAGEMENT & AUTHENTICATION
# ==========================================

def get_user_by_username(username):
    """Fetches user record by username."""
    with get_db() as cursor:
        cursor.execute("SELECT * FROM `users` WHERE `username` = %s", (username,))
        return cursor.fetchone()

def authenticate_user(username, password):
    """
    Validates user login credentials against database records.
    Supports Werkzeug hashed passwords and fallback plain string passwords.
    """
    user = get_user_by_username(username)
    if not user:
        return None, "Invalid username or user does not exist."

    db_password = user['password']

    if db_password.startswith("pbkdf2:") or db_password.startswith("scrypt:"):
        if check_password_hash(db_password, password):
            return user, "Authentication successful."
    else:
        if db_password == password:
            return user, "Authentication successful."

    return None, "Invalid password. Please try again."


# ==========================================
# LOCATIONS CRUD OPERATIONS
# ==========================================

def get_all_locations():
    """Returns list of all registered locations."""
    with get_db() as cursor:
        cursor.execute("SELECT * FROM `locations` ORDER BY `id` ASC")
        return cursor.fetchall()

def get_location_by_id(location_id):
    """Returns location dictionary by ID."""
    with get_db() as cursor:
        cursor.execute("SELECT * FROM `locations` WHERE `id` = %s", (location_id,))
        return cursor.fetchone()

def add_location(name, loc_type, latitude, longitude, emergency_level='None'):
    """Inserts a new location into database."""
    with get_db() as cursor:
        cursor.execute("""
            INSERT INTO `locations` (`name`, `type`, `latitude`, `longitude`, `emergency_level`)
            VALUES (%s, %s, %s, %s, %s)
        """, (name, loc_type, float(latitude), float(longitude), emergency_level))
        return cursor.lastrowid

def update_location(location_id, name, loc_type, latitude, longitude, emergency_level):
    """Updates an existing location record."""
    with get_db() as cursor:
        cursor.execute("""
            UPDATE `locations`
            SET `name` = %s, `type` = %s, `latitude` = %s, `longitude` = %s, `emergency_level` = %s
            WHERE `id` = %s
        """, (name, loc_type, float(latitude), float(longitude), emergency_level, location_id))
        return cursor.rowcount > 0

def delete_location(location_id):
    """Deletes a location by ID."""
    with get_db() as cursor:
        cursor.execute("DELETE FROM `locations` WHERE `id` = %s", (location_id,))
        return cursor.rowcount > 0


# ==========================================
# ROADS CRUD OPERATIONS (GRAPH EDGES)
# ==========================================

def get_all_roads():
    """
    Returns all road connections with joined source and destination location names.
    """
    with get_db() as cursor:
        cursor.execute("""
            SELECT 
                r.id,
                r.source_id,
                l1.name AS source_name,
                l1.type AS source_type,
                r.destination_id,
                l2.name AS destination_name,
                l2.type AS destination_type,
                r.distance,
                r.status,
                r.created_at
            FROM `roads` r
            JOIN `locations` l1 ON r.source_id = l1.id
            JOIN `locations` l2 ON r.destination_id = l2.id
            ORDER BY r.id ASC
        """)
        return cursor.fetchall()

def add_road(source_id, destination_id, distance, status='Open'):
    """Adds a road connection between two locations."""
    if int(source_id) == int(destination_id):
        raise ValueError("Source and destination locations cannot be identical.")

    with get_db() as cursor:
        cursor.execute("""
            INSERT INTO `roads` (`source_id`, `destination_id`, `distance`, `status`)
            VALUES (%s, %s, %s, %s)
        """, (source_id, destination_id, float(distance), status))
        return cursor.lastrowid

def update_road(road_id, source_id, destination_id, distance, status):
    """Updates an existing road connection."""
    with get_db() as cursor:
        cursor.execute("""
            UPDATE `roads`
            SET `source_id` = %s, `destination_id` = %s, `distance` = %s, `status` = %s
            WHERE `id` = %s
        """, (source_id, destination_id, float(distance), status, road_id))
        return cursor.rowcount > 0

def delete_road(road_id):
    """Deletes a road connection by ID."""
    with get_db() as cursor:
        cursor.execute("DELETE FROM `roads` WHERE `id` = %s", (road_id,))
        return cursor.rowcount > 0


# ==========================================
# EMERGENCIES CRUD OPERATIONS
# ==========================================

def get_all_emergencies():
    """
    Returns list of all emergency requests with joined location details.
    """
    with get_db() as cursor:
        cursor.execute("""
            SELECT 
                e.id,
                e.location_id,
                l1.name AS location_name,
                l1.type AS location_type,
                e.people_affected,
                e.emergency_level,
                e.destination_id,
                l2.name AS destination_name,
                e.description,
                e.status,
                e.created_at
            FROM `emergencies` e
            JOIN `locations` l1 ON e.location_id = l1.id
            LEFT JOIN `locations` l2 ON e.destination_id = l2.id
            ORDER BY e.created_at DESC
        """)
        return cursor.fetchall()

def add_emergency(location_id, people_affected, emergency_level, destination_id=None, description=""):
    """Creates a new emergency request."""
    with get_db() as cursor:
        dest = destination_id if destination_id else None
        cursor.execute("""
            INSERT INTO `emergencies` (`location_id`, `people_affected`, `emergency_level`, `destination_id`, `description`, `status`)
            VALUES (%s, %s, %s, %s, %s, 'Pending')
        """, (location_id, int(people_affected), emergency_level, dest, description))

        cursor.execute("""
            UPDATE `locations`
            SET `emergency_level` = %s
            WHERE `id` = %s
        """, (emergency_level, location_id))

        return cursor.lastrowid

def update_emergency_status(emergency_id, status):
    """Updates status of emergency ('Pending', 'In Progress', 'Resolved')."""
    with get_db() as cursor:
        cursor.execute("""
            UPDATE `emergencies`
            SET `status` = %s
            WHERE `id` = %s
        """, (status, emergency_id))
        return cursor.rowcount > 0

def delete_emergency(emergency_id):
    """Deletes an emergency record."""
    with get_db() as cursor:
        cursor.execute("DELETE FROM `emergencies` WHERE `id` = %s", (emergency_id,))
        return cursor.rowcount > 0


# ==========================================
# DASHBOARD STATS
# ==========================================

def get_dashboard_stats():
    """
    Retrieves summary statistics for the dashboard cards and lists.
    """
    with get_db() as cursor:
        # Count Disaster Areas
        cursor.execute("SELECT COUNT(*) AS count FROM `locations` WHERE `type` = 'Disaster Area'")
        total_disasters = cursor.fetchone()['count']

        # Count Rescue Centers
        cursor.execute("SELECT COUNT(*) AS count FROM `locations` WHERE `type` = 'Rescue Center'")
        total_rescue_centers = cursor.fetchone()['count']

        # Count Hospitals
        cursor.execute("SELECT COUNT(*) AS count FROM `locations` WHERE `type` = 'Hospital'")
        total_hospitals = cursor.fetchone()['count']

        # Count Active Emergencies (Pending or In Progress)
        cursor.execute("SELECT COUNT(*) AS count FROM `emergencies` WHERE `status` != 'Resolved'")
        active_emergencies = cursor.fetchone()['count']

        # Count Total Roads & Blocked Roads
        cursor.execute("SELECT COUNT(*) AS total, SUM(CASE WHEN `status` = 'Blocked' THEN 1 ELSE 0 END) AS blocked FROM `roads`")
        road_stats = cursor.fetchone()

        # Recent 5 emergencies
        cursor.execute("""
            SELECT 
                e.id,
                l1.name AS location_name,
                e.people_affected,
                e.emergency_level,
                e.status,
                e.created_at
            FROM `emergencies` e
            JOIN `locations` l1 ON e.location_id = l1.id
            ORDER BY e.id DESC
            LIMIT 5
        """)
        recent_emergencies = cursor.fetchall()

        return {
            'total_disasters': total_disasters,
            'total_rescue_centers': total_rescue_centers,
            'total_hospitals': total_hospitals,
            'active_emergencies': active_emergencies,
            'total_roads': road_stats['total'] if road_stats and road_stats['total'] else 0,
            'blocked_roads': road_stats['blocked'] if road_stats and road_stats['blocked'] else 0,
            'recent_emergencies': recent_emergencies
        }
