# Disaster Rescue Route Planner 🚨🗺️
**A Data Structures & Algorithms Mini Project**

---

## 1. Project Title
**Disaster Rescue Route Planner**

---

## 2. Problem Statement
During severe natural or man-made disasters (such as flash floods, landslides, or earthquakes), rescue teams face major challenges:
* Critical roads may become blocked or submerged.
* Multiple rescue requests flood in simultaneously, requiring swift prioritization.
* Reaching injured victims or evacuating them to hospitals via suboptimal or blocked routes costs vital time.

The **Disaster Rescue Route Planner** solves this problem by representing disaster zones, rescue centers, and hospitals as a dynamic graph network. It calculates the fastest available, open route avoiding blocked roads, while prioritizing emergency requests using a Priority Queue.

---

## 3. Objective
* To build a complete web application using **Python Flask**, **MySQL**, **HTML5/CSS3/JavaScript**.
* To implement fundamental Data Structures (Graph using Adjacency List, Max-Heap Priority Queue) and Algorithms (Dijkstra's Shortest Path, Breadth-First Search) directly in Python code.
* To provide role-based management (Admin & Rescue Team) with an intuitive dashboard and route calculation visualizer.

---

## 4. Required Features
1. **Login & Session Management**:
   * Username and password authentication with role-based access control (Admin / Rescue Team).
2. **Command Dashboard**:
   * Display live counts of Disaster Locations, Rescue Centers, Hospitals, Active Emergencies, and Road Statuses.
   * Recent rescue requests summary.
3. **Location Management (Graph Vertices)**:
   * CRUD operations for locations (Disaster Area, Rescue Center, Hospital, Safe Zone) with latitude/longitude coordinates and emergency levels.
4. **Road Connection Management (Graph Edges)**:
   * Define roads between locations with distance weights and status (`Open` or `Blocked`).
5. **Emergency Requests & Dispatching**:
   * Users can report emergency situations with affected victim counts and severity levels (`Critical`, `High`, `Medium`, `Low`).
6. **Priority Queue**:
   * Automatic backend prioritization where `Critical` life-threatening emergencies are processed before lower priority requests.
7. **Route Finder & Visualizer**:
   * Calculate shortest available path using **Dijkstra's Algorithm** or **BFS Traversal**.
   * Ignores blocked roads automatically.
   * Visualizes step-by-step route hops, total distance (in km), and node traversal sequence.

---

## 5. Technology Stack
* **Frontend**: HTML5, CSS3, JavaScript (Vanilla JS, FontAwesome, Responsive Flexbox/Grid UI)
* **Backend**: Python 3.14 / Flask framework
* **Database**: MySQL (`disaster_rescue_db`) via PyMySQL
* **Data Structures & Algorithms**: Pure Python implementation (`algorithms/` directory)

---

## 6. Data Structures Used

### A. Graph using Adjacency List (`algorithms/graph.py`)
* **Representation**: `dict` mapping location IDs to lists of `Edge` objects:
  ```python
  adj_list = {
      source_id: [Edge(target_id, distance, status='Open'), ...]
  }
  ```
* **Why**: Memory efficient ($O(V + E)$ space complexity) and allows $O(1)$ vertex lookup and fast neighbor iteration.

### B. Priority Queue using Max-Heap (`algorithms/priority_queue.py`)
* **Representation**: Python's `heapq` module wrapped to implement Max-Heap logic with tuple keying:
  ```python
  tuple_entry = (-priority_weight, -people_affected, counter, emergency_item)
  ```
* **Priority Order**:
  1. `Critical` (Weight 4)
  2. `High` (Weight 3)
  3. `Medium` (Weight 2)
  4. `Low` (Weight 1)
* **Tie-Breaking**: Higher victim count receives priority.

---

## 7. Algorithms Used

### A. Dijkstra's Shortest Path Algorithm (`algorithms/dijkstra.py`)
* Computes minimum cumulative road distance between starting disaster location and target hospital/rescue center.
* Dynamically filters out blocked roads (`edge.status == 'Blocked'`).
* Time Complexity: $O((V + E) \log V)$ using Min-Heap priority queue.

### B. Breadth-First Search (BFS) (`algorithms/bfs.py`)
* Traverses graph level-by-level using a FIFO Queue (`collections.deque`).
* Finds the path with the minimum number of road hops/junctions.
* Time Complexity: $O(V + E)$.

---

## 8. Database Design (`database.sql`)
Database Name: `disaster_rescue_db`

### Tables & Schema
1. **`users`**:
   * `id` (INT PK AUTO_INCREMENT)
   * `username` (VARCHAR(50) UNIQUE)
   * `password` (VARCHAR(255))
   * `role` (ENUM('Admin', 'Rescue Team'))
   * `full_name` (VARCHAR(100))
2. **`locations`**:
   * `id` (INT PK AUTO_INCREMENT)
   * `name` (VARCHAR(100) UNIQUE)
   * `type` (ENUM('Disaster Area', 'Rescue Center', 'Hospital', 'Safe Zone'))
   * `latitude` (DECIMAL(10,6)), `longitude` (DECIMAL(10,6))
   * `emergency_level` (ENUM('None', 'Low', 'Medium', 'High', 'Critical'))
3. **`roads`**:
   * `id` (INT PK AUTO_INCREMENT)
   * `source_id` (INT FK -> `locations.id`)
   * `destination_id` (INT FK -> `locations.id`)
   * `distance` (DECIMAL(8,2))
   * `status` (ENUM('Open', 'Blocked'))
4. **`emergencies`**:
   * `id` (INT PK AUTO_INCREMENT)
   * `location_id` (INT FK -> `locations.id`)
   * `people_affected` (INT)
   * `emergency_level` (ENUM('Critical', 'High', 'Medium', 'Low'))
   * `destination_id` (INT FK -> `locations.id`)
   * `description` (TEXT)
   * `status` (ENUM('Pending', 'In Progress', 'Resolved'))

---

## 9. Project Structure

```
DisasterRescuePlanner/
│
├── app.py                     # Main Flask Application & REST API Endpoints
├── config.py                  # Database & App Settings
├── database.py                # PyMySQL Database Layer & Helper Methods
├── requirements.txt           # Dependency Requirements
├── database.sql               # Database Schema Creation & Seed Script
├── README.md                  # Project Documentation
│
├── algorithms/                # Pure Data Structures & Algorithms
│   ├── graph.py               # Adjacency List Graph Data Structure
│   ├── dijkstra.py            # Dijkstra Shortest Path Algorithm
│   ├── bfs.py                 # Breadth-First Search Traversal Algorithm
│   └── priority_queue.py      # Max-Heap Emergency Priority Queue
│
├── templates/                 # Jinja2 HTML Templates
│   ├── login.html             # User Authentication Page
│   ├── dashboard.html         # Main Command Dashboard
│   ├── locations.html         # Location CRUD Management Page
│   ├── roads.html             # Road Network & Graph Edges Page
│   ├── emergencies.html       # Emergency Priority Queue Page
│   └── route_finder.html      # Dijkstra & BFS Route Finder Page
│
└── static/                    # Frontend Assets
    ├── css/
    │   └── style.css          # App CSS Stylesheet
    └── js/
        └── script.js          # AJAX & Route Visualizer Scripts
```

---

## 10. Installation & Setup Instructions

### Prerequisites
* Python 3.8 or higher installed.
* MySQL Server (e.g. MySQL Server, XAMPP MySQL, WAMP, or MySQL Workbench).

### Step 1: Install Python Dependencies
Open terminal/command prompt in the `DisasterRescuePlanner` folder:
```bash
pip install -r requirements.txt
```

### Step 2: Database Setup (MySQL)
1. Start your MySQL service.
2. Login to MySQL shell:
   ```bash
   mysql -u root -p
   ```
3. Import `database.sql` script:
   ```sql
   SOURCE database.sql;
   ```
   *Or execute `database.sql` in MySQL Workbench / phpMyAdmin.*

4. Configure database credentials in `config.py` if your MySQL root has a password:
   ```python
   MYSQL_HOST = 'localhost'
   MYSQL_USER = 'root'
   MYSQL_PASSWORD = 'your_mysql_password' # Update if needed
   MYSQL_DB = 'disaster_rescue_db'
   ```

---

## 11. How to Run the Application

Execute the Flask server:
```bash
python app.py
```
Open your browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 12. Sample Login Credentials

| Role | Username | Password | Access Rights |
|---|---|---|---|
| **Admin** | `admin` | `admin123` | Full Access (CRUD Locations, CRUD Roads, View Queue, Calculate Routes) |
| **Rescue Team** | `rescuer` | `user123` | Report Emergencies, View Queue, Update Status, Calculate Routes |

---

## 13. Future Enhancements
* **Leaflet/Google Maps Visualizer**: Integrate live GPS markers and interactive map polylines for routes.
* **Real-time WebSockets**: Live broadcast updates when new critical emergencies are submitted.
* **Resource Optimization Algorithm**: Dynamic Knapsack algorithm to assign rescue vehicles based on vehicle capacity and victim count.
