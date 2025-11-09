from flask import Flask, jsonify, request
from datetime import datetime
import sqlite3
import argparse
import os

import waitress

import seed # Seeds the database
import utils # Includes several utility functions

parser = argparse.ArgumentParser()
parser.add_argument("-d", "--dev", help="Run in Development mode", type=bool, action=argparse.BooleanOptionalAction)

seed.init_db()

con = sqlite3.connect('containers.db', check_same_thread=False)
cur = con.cursor()

app = Flask(__name__)

# File upload configuration
app.config['UPLOAD_FOLDER'] = "./files"
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

@app.route("/")
def hello_world():
    return "<p>Hello, BIT!</p>"

# Login
# Returns status code which allows user to log in or not (200: OK, 404: Not authorized)
@app.route("/login", methods=["POST"])
def login():
    if not request.is_json:
        return jsonify({"error": "Request was not provided in a valid format or mimetype was not set to application/json."}), 400
    data = request.get_json()
    username = data['username']
    password = data['password']
    
    if username == "manager" and password == "manager123":
        return "", 200
    return jsonify({
        "error": "username or password or combination is not correct. Correct username and password are provided in the user manual."
    }), 401

# Orders
# Returns all orders in the DB to the client.
@app.route("/orders")
def get_orders():
    cur.execute("""
        SELECT o.id, c.id, s.end_time, l.label FROM client_order o
        JOIN shipment s ON s.id=o.shipment_id
        JOIN container c ON c.id=o.container_id
        JOIN location l ON l.id=s.location_id
    """)
    orders = cur.fetchall()
    formatted_orders = [{
        'mainText': f'Container {order[1]}',
        'detailText': f'Arrives in {utils.natural_time(order[2])} from {order[3]}',
        'link': order[0]
    } for order in orders]
    return jsonify(formatted_orders), 200

# Allows client to create new orders.
# Client should provide container_id and shipping_method
@app.route("/orders", methods=['POST'])
def create_order():
    if not request.is_json: return jsonify({"error": "Provided data is not in JSON format or mimetype is not set to application/json."}), 400

    data = request.get_json()
    shipping_method = data['shipping_method']
    selected_container_id = data['container_id']

    if not shipping_method or not selected_container_id:
        return jsonify({"error": "not all required data provided, shipping_method and container_id are required."}), 400

    # Add shipment to DB
    # First fetch location of current container
    cur.execute('SELECT c.location_id FROM container c WHERE c.id=?', (selected_container_id,))
    location_id = cur.fetchone()

    # Calculate container arrival date
    today = datetime.today()
    arrival, _ = utils.calculate_shipment_cost_and_arrival(today, shipping_method)

    # Insert shipment into DB
    cur.execute('INSERT INTO shipment (location_id, start_time, end_time, transport_type, status) VALUES (?,?,?,?,?)', (location_id[0], today.timestamp(), arrival.timestamp(), shipping_method, "Container has been marked for retour",))

    # Insert order into DB
    cur.execute('INSERT INTO client_order (container_id, product_id, shipment_id, client_id) VALUES (?,?,?,?)', (selected_container_id, 1, cur.lastrowid, 1))
    con.commit()

    return "", 201

# Returns specific order and details about it to the client.
@app.route("/orders/<order_id>")
def get_order(order_id):
    cur.execute("""
        SELECT o.id, c.id, s.end_time, s.transport_type, s.status, l.lat, l.lon, l.label FROM client_order o
        JOIN shipment s ON s.id=o.shipment_id
        JOIN container c ON c.id=o.container_id
        JOIN location l ON l.id=s.location_id
        WHERE o.id=?
    """, (int(order_id),))
    order = cur.fetchone()
    if order is None: return jsonify({"error": "There was no order found with that id."}), 404

    return jsonify({
        'container_id': order[1],
        'shipment_end_time': order[2],
        'shipment_transport_type': utils.format_shipment_type(order[3]),
        'shipment_status': order[4],
        'lat': order[5],
        'lon': order[6],
        'location_label': order[7]
    }), 200

# Containers
# Returns a list of all containers in the DB to the client.
@app.route("/containers")
def get_containers():
    cur.execute("""
        SELECT c.id, cmd.status FROM container c
        JOIN container_meta_data cmd ON cmd.id=c.meta_data_id
    """)
    containers = cur.fetchall()
    formatted_containers = []
    for container in containers:
        formatted_containers.append({
            'container_id': container[0],
            'status': container[1]
        })
    return jsonify(formatted_containers), 200

# Returns a list of all containers and their locations to the client.
@app.route("/containers/locations")
def get_container_locations():
    cur.execute("""
        SELECT c.id, l.lat, l.lon FROM container c
        JOIN location l ON l.id=c.location_id
    """)
    locations = cur.fetchall()
    formatted_locations = []
    for location in locations:
        formatted_locations.append({
            'container_id': location[0],
            'lat': location[1],
            'lon': location[2]
        })
    return jsonify(formatted_locations), 200

@app.route("/containers/<container_id>", methods=["DELETE"])
def scrap_container(container_id: str):
    cur.execute("""
        DELETE FROM containers c WHERE c.id=?
    """, (container_id,))
    # Check if any rows are affected, if not, return 404 container not found.
    if cur.rowcount == 0: return jsonify({"error": "The container you are trying to scrap was not found."})
    con.commit()
    return "", 200

# Maintenance
# Returns a list of all maintenance actions currently going on or planned to the client.
@app.route("/maintenance")
def get_maintenance():
    cur.execute("""
        SELECT m.id, c.id, m.maintenance_type, l.label FROM maintenance m
        JOIN container c on c.id=m.container_id
        JOIN location l on l.id=c.location_id
    """)
    maintenance = cur.fetchall()
    formatted_maintenance = []
    for maintenance_object in maintenance:
        formatted_maintenance.append({
            "mainText": maintenance_object[1] + ' - ' + utils.formatted_maintenance_type(maintenance_object[2]),
            "detailText": 'at ' + maintenance_object[3],
            "link": maintenance_object[0]
        })
    return jsonify(formatted_maintenance), 200

# Schedules new maintence, client provides container_id maintenance_type and date in request body.
@app.route("/maintenance", methods=['POST'])
def schedule_new_maintenance():
    if not request.is_json: return jsonify({"error": "Provided body is not in JSON form or mimetype is not set to application/json"}), 400
    data = request.get_json()

    # Validate required fields
    if not data or 'container_id' not in data or 'maintenance_type' not in data or 'date' not in data:
        return jsonify({"error": "container_id, maintenance_type, and date (dd/mm/yyyy) are required"}), 400

    container_id = data.get('container_id')
    maintenance_type = data.get('maintenance_type')
    date_str = data.get('date')

    # NOT IMPLEMENTED IN DB, maintenance date is not stored
    # Parse date in dd/mm/yyyy format
    # try:
    #     maintenance_date = datetime.strptime(date_str, "%d/%m/%Y")
    # except ValueError:
    #     return jsonify({"error": "Date must be in dd/mm/yyyy format"}), 400

    # Check if container exists
    cur.execute("SELECT id FROM container WHERE id=?", (container_id,))
    container = cur.fetchone()
    if not container:
        return jsonify({"error": "Container not found"}), 404

    # Validate maintenance_type
    if maintenance_type.lower() not in ['deepclean', 'outside_repairs']:
        return jsonify({"error": "maintenance_type must be 'deepclean' or 'outside_repairs'"}), 400

    # Create maintenance entry
    cur.execute("""
        INSERT INTO maintenance (container_id, maintenance_type, status)
        VALUES (?, ?, ?)
    """, (container_id, maintenance_type.lower(), 'scheduled'))
    maintenance_id = cur.lastrowid

    con.commit()

    return jsonify({
        "message": "Maintenance scheduled successfully",
        "maintenance_id": maintenance_id,
        "container_id": container_id,
        "maintenance_type": maintenance_type,
        "scheduled_date": date_str
    }), 201

# Returns specific maintenence and its details to the client.
@app.route("/maintenance/<maintenance_id>")
def get_maintenance_by_id(maintenance_id):
    cur.execute("""
        SELECT m.id, c.id, m.maintenance_type, m.status FROM maintenance m
        JOIN container c ON c.id=m.container_id
        WHERE m.id=?
    """, (int(maintenance_id),))
    maintenance = cur.fetchone()
    return jsonify({
        "maintenance_id": maintenance[0],
        "container_id": maintenance[1],
        "maintenance_type": utils.formatted_maintenance_type(maintenance[2]),
        "maintenance_status": maintenance[3]
    }), 200

# Returns all files associated with a maintenance_id to the client
@app.route("/maintenance/<maintenance_id>/files")
def get_maintenance_files(maintenance_id: int):
    cur.execute("""
        SELECT file_name, file_type FROM report_file
        WHERE maintenance_id=?                
    """, (int(maintenance_id),))
    files = cur.fetchmany()
    
    formatted_files = [{
        'mainText': 'Image evidence' if file[1] == 'image' else 'Maintenance report',
        'detailText': 'filename: ' + file[0],
        'imageName': utils.get_client_file_asset_name(file[1])
    } for file in files]

    return jsonify(formatted_files), 200

# Allows client to upload a file to the server associated with maintenance. Can either be a report (pdf) or image (png, jpg etc.)
@app.route("/maintenance/<maintenance_id>/files", methods=["POST"])
def upload_maintenance_image(maintenance_id: int):
    print(len(request.files))
    if not "file" in request.files.keys(): return jsonify({"error": "The request did not include a file upload named 'file'. Please try again."}), 400
    file = request.files['file']
    if file.filename is None:
        return jsonify({"error": "No file was provided. Please upload a file to save it."}), 400
    if file.content_length > app.config["MAX_CONTENT_LENGTH"]:
        return jsonify({"error": "The provided file was too big. Please upload a file smaller than 16Mb."}), 400
    
    _, file_extension = os.path.splitext(file.filename)
    if file_extension == "": return jsonify({"error": "The provided file did not include an extension. Please rename the file wih an extension"}), 400
    file_type = utils.get_file_type(file_extension)
    if file_type == None: return jsonify({"error": "Uploaded file type is not supported."}), 400
    generated_file_name = utils.generate_file_name(maintenance_id) + file_extension

    file.save(os.path.join(app.config["UPLOAD_FOLDER"], generated_file_name))
    
    cur.execute("""
        INSERT INTO report_file (maintenance_id, type, file_type, file_name) VALUES (?,?,?,?)
    """, (maintenance_id, 'maintenance', file_type, generated_file_name))
    con.commit()
    return "", 201


if __name__ == '__main__':
    args = parser.parse_args()
    if args.dev:
        app.run(host='0.0.0.0', port=8080, debug=True)
    else:
        waitress.serve(app)