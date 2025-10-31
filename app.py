from flask import Flask, jsonify, request
from datetime import datetime, timedelta
import sqlite3
import humanize
import waitress
import argparse
import seed
import utils
import os
from werkzeug.utils import secure_filename
import uuid

parser = argparse.ArgumentParser()
parser.add_argument("-d", "--dev", help="Run in Development mode", type=bool, action=argparse.BooleanOptionalAction)

seed.init_db()

con = sqlite3.connect('containers.db', check_same_thread=False)
cur = con.cursor()

app = Flask(__name__)

# File upload configuration
UPLOAD_FOLDER = '/app/storage'  # Docker storage path
ALLOWED_PHOTO_EXTENSIONS = {'jpg', 'jpeg', 'png'}
ALLOWED_PDF_EXTENSIONS = {'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create upload directories if they don't exist
os.makedirs(os.path.join(UPLOAD_FOLDER, 'photos'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'pdfs'), exist_ok=True)

def allowed_photo_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_PHOTO_EXTENSIONS

def allowed_pdf_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_PDF_EXTENSIONS

@app.route("/")
def hello_world():
    return "<p>Hello, BIT!</p>"

# Orders
@app.route("/orders")
def get_orders():
    cur.execute("""
        SELECT o.id, c.id, s.end_time, l.label FROM client_order o
        JOIN shipment s ON s.id=o.shipment_id
        JOIN container c ON c.id=o.container_id
        JOIN location l ON l.id=s.location_id
    """)
    orders = cur.fetchall()
    formatted_orders = []
    for order in orders:
        formatted_orders.append({
            'mainText': f'Container {order[1]}',
            'detailText': f'Arrives in {humanize.naturaltime(order[2] / 1000, future=True)} from {order[3]}',
            'link': order[0]
        })
    return jsonify(formatted_orders), 200

@app.route("/orders/<order_id>")
def get_order(order_id):
    def format_shipment_type(shipment_type):
        if shipment_type == 'sea':
            return 'Transporting over sea.'
        elif shipment_type == 'air':
            return 'Transporting through air.'
        else:
            return 'Transporting over land.'

    cur.execute(f"""
        SELECT o.id, c.id, s.end_time, s.transport_type, s.status, l.lat, l.lon, l.label FROM client_order o
        JOIN shipment s ON s.id=o.shipment_id
        JOIN container c ON c.id=o.container_id
        JOIN location l ON l.id=s.location_id
        WHERE o.id={order_id}
    """)
    order = cur.fetchone()
    return jsonify({
        'container_id': order[1],
        'shipment_end_time': order[2],
        'shipment_transport_type': format_shipment_type(order[3]),
        'shipment_status': order[4],
        'lat': order[5],
        'lon': order[6],
        'location_label': order[7]
    }), 200

@app.route("/orders/new", methods=['POST'])
def create_new_order():
    import random

    data = request.get_json()

    # Validate required fields
    if not data or 'transport_type' not in data:
        return jsonify({"error": "transport_type is required (Land, Sea, or Air)"}), 400

    transport_type = data.get('transport_type')

    # Validate transport type
    transport_type_lower = transport_type.lower()
    if transport_type_lower not in ['land', 'sea', 'air']:
        return jsonify({"error": "transport_type must be 'Land', 'Sea', or 'Air'"}), 400

    # Get optional fields or use defaults
    product_id = data.get('product_id', 1)  # Default to first product
    client_id = data.get('client_id', 1)  # Default to first client

    # Verify product and client exist
    cur.execute("SELECT id FROM product WHERE id=?", (product_id,))
    if not cur.fetchone():
        return jsonify({"error": "Product not found"}), 404

    cur.execute("SELECT id FROM client WHERE id=?", (client_id,))
    if not cur.fetchone():
        return jsonify({"error": "Client not found"}), 404

    # Get all containers and randomly select one
    cur.execute("SELECT id, location_id FROM container")
    containers = cur.fetchall()

    if not containers:
        return jsonify({"error": "No containers available"}), 404

    selected_container = random.choice(containers)
    container_id = selected_container[0]
    location_id = selected_container[1]

    # Calculate dates and costs based on transport type
    today = datetime.today()
    start_time = int(today.timestamp())
    end_time = None
    cost = None

    if transport_type_lower == 'land':
        end_time = int((today + timedelta(days=5)).timestamp())
        cost = 10_000 * 5
    elif transport_type_lower == 'sea':
        end_time = int((today + timedelta(weeks=2)).timestamp())
        cost = 1_000 * 14
    elif transport_type_lower == 'air':
        end_time = int((today + timedelta(days=2)).timestamp())
        cost = 100_000 * 2

    # Create shipment
    cur.execute("""
        INSERT INTO shipment (location_id, start_time, end_time, transport_type, status)
        VALUES (?, ?, ?, ?, ?)
    """, (location_id, start_time, end_time, transport_type_lower, 'Getting ready for shipment'))
    shipment_id = cur.lastrowid

    # Create client order
    cur.execute("""
        INSERT INTO client_order (container_id, product_id, shipment_id, client_id)
        VALUES (?, ?, ?, ?)
    """, (container_id, product_id, shipment_id, client_id))
    order_id = cur.lastrowid

    con.commit()

    return jsonify({
        "message": "Order created successfully",
        "order_id": order_id,
        "shipment_id": shipment_id,
        "container_id": container_id,
        "location_id": location_id,
        "product_id": product_id,
        "client_id": client_id,
        "transport_type": transport_type_lower,
        "start_time": start_time,
        "end_time": end_time,
        "cost": f"€ {cost}",
        "status": "Getting ready for shipment"
    }), 201

# Containers
@app.route("/containers")
def get_containers():
    cur.execute("""
        SELECT c.id FROM container c
    """)
    containers = cur.fetchall()
    formatted_containers = []
    for container in containers:
        formatted_containers.append({
            'mainText': container[0]
        })
    return jsonify(formatted_containers), 200

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

# Maintenance
def formatted_maintenance_type(maintenance_type):
    if maintenance_type == 'deepclean':
        return 'Deep clean'
    else:
        return 'Outside repairs'

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
            "mainText": maintenance_object[1] + ' - ' + formatted_maintenance_type(maintenance_object[2]),
            "detailText": 'at ' + maintenance_object[3],
            "link": maintenance_object[0]
        })
    return jsonify(formatted_maintenance), 200

@app.route("/maintenance/<maintenance_id>")
def get_maintenance_by_id(maintenance_id):
    cur.execute(f"""
        SELECT m.id, c.id, m.maintenance_type, m.status, m.photo_path, m.pdf_path FROM maintenance m
        JOIN container c ON c.id=m.container_id
        WHERE m.id={maintenance_id}
    """)
    maintenance = cur.fetchone()
    return jsonify({
        "maintenance_id": maintenance[0],
        "container_id": maintenance[1],
        "maintenance_type": formatted_maintenance_type(maintenance[2]),
        "maintenance_status": maintenance[3],
        "photo_path": maintenance[4],
        "pdf_path": maintenance[5]
    }), 200

@app.route("/maintenance/schedulenew", methods=['POST'])
def schedule_new_maintenance():
    data = request.get_json()

    # Validate required fields
    if not data or 'container_id' not in data or 'maintenance_type' not in data or 'date' not in data:
        return jsonify({"error": "container_id, maintenance_type, and date (dd/mm/yyyy) are required"}), 400

    container_id = data.get('container_id')
    maintenance_type = data.get('maintenance_type')
    date_str = data.get('date')

    # Parse date in dd/mm/yyyy format
    try:
        maintenance_date = datetime.strptime(date_str, "%d/%m/%Y")
    except ValueError:
        return jsonify({"error": "Date must be in dd/mm/yyyy format"}), 400

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

@app.route("/maintenance/<maintenance_id>/upload-photo", methods=['POST'])
def upload_maintenance_photo(maintenance_id):
    # Check if maintenance exists
    cur.execute("SELECT id FROM maintenance WHERE id=?", (maintenance_id,))
    maintenance = cur.fetchone()
    if not maintenance:
        return jsonify({"error": "Maintenance record not found"}), 404

    # Check if file is present in request
    if 'photo' not in request.files:
        return jsonify({"error": "No photo file provided"}), 400

    file = request.files['photo']

    # Check if file is selected
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    # Validate file type
    if not allowed_photo_file(file.filename):
        return jsonify({"error": "Invalid file type. Allowed types: jpg, jpeg, png"}), 400

    # Generate unique filename to avoid conflicts
    filename = secure_filename(file.filename)
    file_extension = filename.rsplit('.', 1)[1].lower()
    unique_filename = f"{uuid.uuid4()}.{file_extension}"

    # Save file to storage
    photo_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'photos')
    file_path = os.path.join(photo_dir, unique_filename)
    storage_path = f"/app/storage/photos/{unique_filename}"

    try:
        file.save(file_path)

        # Update maintenance record with photo path
        cur.execute("""
            UPDATE maintenance SET photo_path = ? WHERE id = ?
        """, (storage_path, maintenance_id))
        con.commit()

        return jsonify({
            "message": "Photo uploaded successfully",
            "maintenance_id": maintenance_id,
            "photo_path": storage_path,
            "filename": unique_filename
        }), 200

    except Exception as e:
        return jsonify({"error": f"Failed to upload photo: {str(e)}"}), 500

@app.route("/maintenance/<maintenance_id>/upload-pdf", methods=['POST'])
def upload_maintenance_pdf(maintenance_id):
    # Check if maintenance exists
    cur.execute("SELECT id FROM maintenance WHERE id=?", (maintenance_id,))
    maintenance = cur.fetchone()
    if not maintenance:
        return jsonify({"error": "Maintenance record not found"}), 404

    # Check if file is present in request
    if 'pdf' not in request.files:
        return jsonify({"error": "No PDF file provided"}), 400

    file = request.files['pdf']

    # Check if file is selected
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    # Validate file type
    if not allowed_pdf_file(file.filename):
        return jsonify({"error": "Invalid file type. Only PDF files are allowed"}), 400

    # Generate unique filename to avoid conflicts
    filename = secure_filename(file.filename)
    file_extension = filename.rsplit('.', 1)[1].lower()
    unique_filename = f"{uuid.uuid4()}.{file_extension}"

    # Save file to storage
    pdf_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'pdfs')
    file_path = os.path.join(pdf_dir, unique_filename)
    storage_path = f"/app/storage/pdfs/{unique_filename}"

    try:
        file.save(file_path)

        # Update maintenance record with PDF path
        cur.execute("""
            UPDATE maintenance SET pdf_path = ? WHERE id = ?
        """, (storage_path, maintenance_id))
        con.commit()

        return jsonify({
            "message": "PDF uploaded successfully",
            "maintenance_id": maintenance_id,
            "pdf_path": storage_path,
            "filename": unique_filename
        }), 200

    except Exception as e:
        return jsonify({"error": f"Failed to upload PDF: {str(e)}"}), 500
@app.route("/shipments", methods=['POST'])
def create_shipment():
    data = request.get_json()

    # Validate required fields
    if not data:
        return jsonify({"error": "Request body is required"}), 400

    location_id = data.get('location_id')
    transport_type = data.get('transport_type')
    container_id = data.get('container_id')
    product_id = data.get('product_id')
    client_id = data.get('client_id')

    if not all([location_id, transport_type, container_id, product_id, client_id]):
        return jsonify({
            "error": "Missing required fields",
            "required": ["location_id", "transport_type", "container_id", "product_id", "client_id"]
        }), 400

    # Validate transport type
    transport_type = transport_type.lower()
    if transport_type not in ['sea', 'air', 'land']:
        return jsonify({"error": "transport_type must be 'sea', 'air', or 'land'"}), 400

    # Calculate dates and costs based on transport type
    today = datetime.today()
    start_time = int(today.timestamp())
    end_time = None

    if transport_type == 'land':
        end_time = int((today + timedelta(days=5)).timestamp())
    elif transport_type == 'sea':
        end_time = int((today + timedelta(weeks=2)).timestamp())
    elif transport_type == 'air':
        end_time = int((today + timedelta(days=2)).timestamp())

    # Check if referenced entities exist
    cur.execute("SELECT id FROM location WHERE id=?", (location_id,))
    if not cur.fetchone():
        return jsonify({"error": "Location not found"}), 404

    cur.execute("SELECT id FROM container WHERE id=?", (container_id,))
    if not cur.fetchone():
        return jsonify({"error": "Container not found"}), 404

    cur.execute("SELECT id FROM product WHERE id=?", (product_id,))
    if not cur.fetchone():
        return jsonify({"error": "Product not found"}), 404

    cur.execute("SELECT id FROM client WHERE id=?", (client_id,))
    if not cur.fetchone():
        return jsonify({"error": "Client not found"}), 404

    # Create shipment
    cur.execute("""
        INSERT INTO shipment (location_id, start_time, end_time, transport_type, status)
        VALUES (?, ?, ?, ?, ?)
    """, (location_id, start_time, end_time, transport_type, 'Getting ready for shipment'))
    shipment_id = cur.lastrowid

    # Create client order
    cur.execute("""
        INSERT INTO client_order (container_id, product_id, shipment_id, client_id)
        VALUES (?, ?, ?, ?)
    """, (container_id, product_id, shipment_id, client_id))
    order_id = cur.lastrowid

    con.commit()

    return jsonify({
        "message": "Shipment created successfully",
        "shipment_id": shipment_id,
        "order_id": order_id,
        "start_time": start_time,
        "end_time": end_time,
        "transport_type": transport_type,
        "status": "Getting ready for shipment"
    }), 201


if __name__ == '__main__':
    args = parser.parse_args()
    if args.dev:
        app.run(host='0.0.0.0', port=8080, debug=True)
    else:
        waitress.serve(app)