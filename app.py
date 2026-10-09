"""
MAIN FLASK APPLICATION MODULE
=============================
Disaster Rescue Route Planner - Data Structures & Algorithms Mini Project
Flask Server handling page rendering, session authentication, and REST API endpoints.
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from functools import wraps
from config import Config
import database
from algorithms.graph import Graph
from algorithms.dijkstra import dijkstra_shortest_path
from algorithms.bfs import bfs_traversal
from algorithms.priority_queue import EmergencyPriorityQueue, EmergencyItem

app = Flask(__name__)
app.config.from_object(Config)

# Try initializing DB schema on app startup
with app.app_context():
    db_ok, db_msg = database.init_db()
    if not db_ok:
        print(f"[Warning] DB initialization failed on startup: {db_msg}")


# ==========================================
# AUTHENTICATION & DECORATORS
# ==========================================

def login_required(f):
    """Decorator to protect routes requiring user login."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Authentication required. Please log in.'}), 401
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to restrict routes to Admin users only."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Authentication required.'}), 401
            return redirect(url_for('login_page'))
        if session.get('role') != 'Admin':
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Admin permission required.'}), 403
            return redirect(url_for('dashboard_page'))
        return f(*args, **kwargs)
    return decorated_function


# ==========================================
# PAGE ROUTE RENDERING
# ==========================================

@app.route('/')
def index():
    return redirect(url_for('login_page'))

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

@app.route('/dashboard')
@login_required
def dashboard_page():
    return render_template('dashboard.html', user=session)

@app.route('/locations')
@login_required
def locations_page():
    return render_template('locations.html', user=session)

@app.route('/roads')
@login_required
def roads_page():
    return render_template('roads.html', user=session)

@app.route('/emergencies')
@login_required
def emergencies_page():
    return render_template('emergencies.html', user=session)

@app.route('/route-finder')
@login_required
def route_finder_page():
    return render_template('route_finder.html', user=session)


# ==========================================
# REST API ENDPOINTS
# ==========================================

# 1. Authentication API
@app.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return jsonify({'success': False, 'message': 'Username and password are required.'}), 400

    try:
        user, msg = database.authenticate_user(username, password)
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['full_name'] = user['full_name']
            return jsonify({
                'success': True,
                'message': 'Login successful!',
                'user': {
                    'id': user['id'],
                    'username': user['username'],
                    'role': user['role'],
                    'full_name': user['full_name']
                }
            })
        else:
            return jsonify({'success': False, 'message': msg}), 401
    except Exception as e:
        return jsonify({'success': False, 'message': f"Database error during authentication: {str(e)}"}), 500

@app.route('/api/auth/current_user', methods=['GET'])
def api_current_user():
    if 'user_id' in session:
        return jsonify({
            'success': True,
            'user': {
                'id': session['user_id'],
                'username': session['username'],
                'role': session['role'],
                'full_name': session['full_name']
            }
        })
    return jsonify({'success': False, 'user': None})

# 2. Dashboard API
@app.route('/api/dashboard/stats', methods=['GET'])
@login_required
def api_dashboard_stats():
    try:
        stats = database.get_dashboard_stats()
        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# 3. Location CRUD API
@app.route('/api/locations', methods=['GET'])
@login_required
def api_get_locations():
    try:
        locations = database.get_all_locations()
        return jsonify({'success': True, 'locations': locations})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/locations', methods=['POST'])
@admin_required
def api_add_location():
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    loc_type = data.get('type', '').strip()
    latitude = data.get('latitude', 0.0)
    longitude = data.get('longitude', 0.0)
    emergency_level = data.get('emergency_level', 'None').strip()

    valid_types = ['Disaster Area', 'Rescue Center', 'Hospital', 'Safe Zone']
    if not name or loc_type not in valid_types:
        return jsonify({'success': False, 'message': 'Invalid location name or type.'}), 400

    try:
        loc_id = database.add_location(name, loc_type, latitude, longitude, emergency_level)
        return jsonify({'success': True, 'message': 'Location added successfully!', 'location_id': loc_id})
    except Exception as e:
        if "Duplicate entry" in str(e):
            return jsonify({'success': False, 'message': f"A location named '{name}' already exists."}), 400
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/locations/<int:location_id>', methods=['PUT'])
@admin_required
def api_update_location(location_id):
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    loc_type = data.get('type', '').strip()
    latitude = data.get('latitude', 0.0)
    longitude = data.get('longitude', 0.0)
    emergency_level = data.get('emergency_level', 'None').strip()

    try:
        updated = database.update_location(location_id, name, loc_type, latitude, longitude, emergency_level)
        if updated:
            return jsonify({'success': True, 'message': 'Location updated successfully!'})
        return jsonify({'success': False, 'message': 'Location not found.'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/locations/<int:location_id>', methods=['DELETE'])
@admin_required
def api_delete_location(location_id):
    try:
        deleted = database.delete_location(location_id)
        if deleted:
            return jsonify({'success': True, 'message': 'Location deleted successfully!'})
        return jsonify({'success': False, 'message': 'Location not found.'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# 4. Road CRUD API (Graph Management)
@app.route('/api/roads', methods=['GET'])
@login_required
def api_get_roads():
    try:
        roads = database.get_all_roads()
        return jsonify({'success': True, 'roads': roads})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/roads', methods=['POST'])
@admin_required
def api_add_road():
    data = request.get_json() or {}
    source_id = data.get('source_id')
    destination_id = data.get('destination_id')
    distance = data.get('distance')
    status = data.get('status', 'Open')

    if not source_id or not destination_id or distance is None:
        return jsonify({'success': False, 'message': 'Source, destination, and distance are required.'}), 400

    try:
        road_id = database.add_road(source_id, destination_id, distance, status)
        return jsonify({'success': True, 'message': 'Road connection created successfully!', 'road_id': road_id})
    except ValueError as ve:
        return jsonify({'success': False, 'message': str(ve)}), 400
    except Exception as e:
        if "Duplicate entry" in str(e):
            return jsonify({'success': False, 'message': 'A road connection already exists between these locations.'}), 400
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/roads/<int:road_id>', methods=['PUT'])
@admin_required
def api_update_road(road_id):
    data = request.get_json() or {}
    source_id = data.get('source_id')
    destination_id = data.get('destination_id')
    distance = data.get('distance')
    status = data.get('status', 'Open')

    try:
        updated = database.update_road(road_id, source_id, destination_id, distance, status)
        if updated:
            return jsonify({'success': True, 'message': 'Road connection updated successfully!'})
        return jsonify({'success': False, 'message': 'Road connection not found.'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/roads/<int:road_id>', methods=['DELETE'])
@admin_required
def api_delete_road(road_id):
    try:
        deleted = database.delete_road(road_id)
        if deleted:
            return jsonify({'success': True, 'message': 'Road connection deleted successfully!'})
        return jsonify({'success': False, 'message': 'Road connection not found.'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# 5. Emergency Requests & Priority Queue API
@app.route('/api/emergencies', methods=['GET'])
@login_required
def api_get_emergencies():
    try:
        emergencies = database.get_all_emergencies()
        return jsonify({'success': True, 'emergencies': emergencies})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/emergencies/queue', methods=['GET'])
@login_required
def api_get_emergency_queue():
    """
    DATA STRUCTURE: PRIORITY QUEUE ENDPOINT
    Fetches raw emergency records from database and processes them through
    our custom EmergencyPriorityQueue Max-Heap to return strictly prioritized order.
    """
    try:
        raw_emergencies = database.get_all_emergencies()
        pq = EmergencyPriorityQueue()

        for em in raw_emergencies:
            item = EmergencyItem(
                emergency_id=em['id'],
                location_id=em['location_id'],
                location_name=em['location_name'],
                people_affected=em['people_affected'],
                emergency_level=em['emergency_level'],
                destination_id=em['destination_id'],
                destination_name=em['destination_name'],
                description=em['description'],
                status=em['status'],
                created_at=em['created_at']
            )
            pq.push(item)

        # Get sorted queue without mutating
        prioritized_list = pq.get_sorted_queue()
        return jsonify({'success': True, 'priority_queue': prioritized_list, 'total': len(prioritized_list)})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/emergencies', methods=['POST'])
@login_required
def api_add_emergency():
    data = request.get_json() or {}
    location_id = data.get('location_id')
    people_affected = data.get('people_affected', 1)
    emergency_level = data.get('emergency_level', 'Medium')
    destination_id = data.get('destination_id')
    description = data.get('description', '').strip()

    if not location_id:
        return jsonify({'success': False, 'message': 'Disaster location is required.'}), 400

    try:
        em_id = database.add_emergency(location_id, people_affected, emergency_level, destination_id, description)
        return jsonify({'success': True, 'message': 'Emergency request reported successfully!', 'emergency_id': em_id})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/emergencies/<int:emergency_id>/status', methods=['PUT'])
@login_required
def api_update_emergency_status(emergency_id):
    data = request.get_json() or {}
    status = data.get('status', 'Pending')

    if status not in ['Pending', 'In Progress', 'Resolved']:
        return jsonify({'success': False, 'message': 'Invalid status value.'}), 400

    try:
        updated = database.update_emergency_status(emergency_id, status)
        if updated:
            return jsonify({'success': True, 'message': f"Emergency status updated to '{status}'."})
        return jsonify({'success': False, 'message': 'Emergency record not found.'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# 6. Route Calculation API (GRAPH & DIJKSTRA / BFS ALGORITHMS)
@app.route('/api/route/calculate', methods=['POST'])
@login_required
def api_calculate_route():
    """
    ALGORITHMS & DATA STRUCTURE ENDPOINT
    1. Loads Graph Vertices & Edges from MySQL database.
    2. Builds Graph using Adjacency List.
    3. Runs Dijkstra's Algorithm (or BFS Traversal) ignoring blocked roads.
    4. Returns step-by-step route result to frontend.
    """
    data = request.get_json() or {}
    start_id = data.get('start_location_id')
    dest_id = data.get('destination_location_id')
    algorithm = data.get('algorithm', 'dijkstra').lower()  # 'dijkstra' or 'bfs'

    if not start_id or not dest_id:
        return jsonify({'success': False, 'message': 'Please select both Starting location and Destination location.'}), 400

    start_id = int(start_id)
    dest_id = int(dest_id)

    try:
        # Step A: Load Graph from Database
        locations = database.get_all_locations()
        roads = database.get_all_roads()

        graph = Graph()

        # Add all nodes with metadata
        for loc in locations:
            graph.add_node(loc['id'], {
                'id': loc['id'],
                'name': loc['name'],
                'type': loc['type'],
                'latitude': float(loc['latitude']),
                'longitude': float(loc['longitude']),
                'emergency_level': loc['emergency_level']
            })

        # Add all edges (Roads)
        for road in roads:
            graph.add_edge(
                source_id=road['source_id'],
                destination_id=road['destination_id'],
                distance=road['distance'],
                status=road['status'],
                bidirectional=True
            )

        # Step B: Execute chosen algorithm
        if algorithm == 'bfs':
            result = bfs_traversal(graph, start_id, dest_id)
            result['algorithm_used'] = 'Breadth-First Search (BFS) Traversal'
        else:
            result = dijkstra_shortest_path(graph, start_id, dest_id)
            result['algorithm_used'] = "Dijkstra's Shortest Path Algorithm"

        # Provide graph representation stats
        result['total_nodes'] = len(graph.get_nodes())
        result['adj_list_str'] = graph.display_adj_list()

        return jsonify({'success': True, 'result': result})

    except Exception as e:
        return jsonify({'success': False, 'message': f"Error calculating rescue route: {str(e)}"}), 500


if __name__ == '__main__':
    print("=" * 60)
    print("      DISASTER RESCUE ROUTE PLANNER - FLASK SERVER     ")
    print("=" * 60)
    print("Starting server at http://127.0.0.1:5000 ...")
    app.run(host='0.0.0.0', port=5000, debug=True)
