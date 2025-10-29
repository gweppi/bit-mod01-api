from flask import Flask, jsonify
from flask_cors import CORS
import sqlite3
import os
import random

app = Flask(__name__)

CORS(app, resources={r"/*": {"origins": "*"}})

def init_db():
    db_exists = os.path.exists('containers.db')

    if not db_exists:
        print("Database not found. Creating")
        con = sqlite3.connect('containers.db')
        cur = con.cursor()

        with open('../scripts/create_tables.sql', 'r') as f:
            create_tables_script = f.read()
        cur.executescript(create_tables_script)

        # Location data
        location_data = [
            (1, 'Rotterdam', 51.885, 4.286, 2),
            (2, 'Enschede', 52.21833, 6.89583, 45),
            (3, 'Eindhoven', 51.4416, 5.4697, 23)
        ]
        cur.executemany('INSERT INTO location (id, label, lat, lon, alt) VALUES (?,?,?,?,?)', location_data)

        # Shipment data
        shipment_data = [
            (1, 1, 1743590400, 1744704000, 'sea'),
            (2, 1, 1746384000, 1746998400, 'air'),
            (3, 2, 1749331200, 1750464000, 'land'),
            (4, 3, 1750646400, 1751376000, 'land'),
        ]
        cur.executemany('INSERT INTO shipment (id, location_id, start_time, end_time, transport_type) VALUES (?,?,?,?,?)', shipment_data)

        # Container meta data
        length_options = [5, 10, 15, 20, 25]
        weight_options = [10_000, 20_000, 30_000, 35_000]
        container_meta_data = [
            (
                i,
                random.choice(length_options),
                random.choice(length_options),
                random.choice(length_options),
                28,
                random.choice(weight_options),
            )
            for i in range(1, 6)
        ]
        cur.executemany('INSERT INTO container_meta_data (id, length, height, width, volume, weight) VALUES (?,?,?,?,?,?)', container_meta_data)

        # Container data
        container_data = [
            (
                'ASML ' + str(random.randint(10000, 99999)) + ' 4',
                random.randint(1, 4),
                random.randint(1, 6),
                random.randint(1, 20)
            )
            for _ in range(1, 11)
        ]
        cur.executemany('INSERT INTO container (id, location_id, meta_data_id, cycle_count) VALUES (?,?,?,?)', container_data)

        # Product data
        product_data = [
            (1, 'Big Machine', 10_000_000),
            (2, 'Bigger Machine', 20_000_000),
            (3, 'Biggest Machine', 50_000_000)
        ]
        cur.executemany('INSERT INTO product (id, name, price) VALUES (?,?,?)', product_data)

        # Client data
        client_data = [
            (1, 'John Doe', 'One Beer Street'),
            (2, 'TSMC', '123 Strong Street av.'),
            (3, 'Philips', 'Eindhoven 12')
        ]
        cur.executemany('INSERT INTO client (id, name, address) VALUES (?,?,?)', client_data)

        # Client order data
        client_order_data = [
            (
                i,
                random.choice(container_data)[0],
                random.choice(product_data)[0],
                random.choice(shipment_data)[0],
                random.choice(client_data)[0]
            )
            for i in range(1, 21)
        ]
        cur.executemany('INSERT INTO client_order (id, container_id, product_id, shipment_id, client_id) VALUES (?,?,?,?,?)', client_order_data)

        con.commit()
        cur.close()
        con.close()
        print("Database created successfully!")
    else:
        print("Database already exists.")


init_db()

con = sqlite3.connect('containers.db', check_same_thread=False)
cur = con.cursor()

@app.route("/")
def hello_world():
    return "<p>Hello, Sucky !</p>"

# Location endpoints
@app.route("/location/all")
def get_all_locations():
    cur.execute('SELECT * FROM location')
    locations = cur.fetchall()
    return jsonify(locations)

@app.route("/location/<int:id>")
def get_location(id):
    cur.execute('SELECT * FROM location WHERE id = ?', (id,))
    location = cur.fetchone()
    if location:
        return jsonify(location)
    return jsonify({"error": "Location not found"}), 404

# Shipment endpoints
@app.route("/shipment/all")
def get_all_shipments():
    cur.execute('SELECT s.id, s.location_id, l.label, l.lat, l.lon, l.alt, s.start_time, s.end_time, s.transport_type FROM shipment s JOIN location l ON s.location_id = l.id')
    shipments = cur.fetchall()
    return jsonify(shipments)

@app.route("/shipment/<int:id>")
def get_shipment(id):
    cur.execute('SELECT s.id, s.location_id, l.label, l.lat, l.lon, l.alt, s.start_time, s.end_time, s.transport_type FROM shipment s JOIN location l ON s.location_id = l.id WHERE s.id = ?', (id,))
    shipment = cur.fetchone()
    if shipment:
        return jsonify(shipment)
    return jsonify({"error": "Shipment not found"}), 404

# Container endpoints
@app.route("/container/all")
def get_all_containers():
    cur.execute('SELECT * FROM container')
    containers = cur.fetchall()
    return jsonify(containers)

@app.route("/container/<string:id>")
def get_container(id):
    cur.execute('SELECT * FROM container WHERE id = ?', (id,))
    container = cur.fetchone()
    if container:
        return jsonify(container)
    return jsonify({"error": "Container not found"}), 404

# Container meta data endpoints
@app.route("/container_meta_data/all")
def get_all_container_meta_data():
    cur.execute('SELECT * FROM container_meta_data')
    meta_data = cur.fetchall()
    return jsonify(meta_data)

@app.route("/container_meta_data/<int:id>")
def get_container_meta_data(id):
    cur.execute('SELECT * FROM container_meta_data WHERE id = ?', (id,))
    meta_data = cur.fetchone()
    if meta_data:
        return jsonify(meta_data)
    return jsonify({"error": "Container meta data not found"}), 404

# Product endpoints
@app.route("/product/all")
def get_all_products():
    cur.execute('SELECT * FROM product')
    products = cur.fetchall()
    return jsonify(products)

@app.route("/product/<int:id>")
def get_product(id):
    cur.execute('SELECT * FROM product WHERE id = ?', (id,))
    product = cur.fetchone()
    if product:
        return jsonify(product)
    return jsonify({"error": "Product not found"}), 404

# Client endpoints
@app.route("/client/all")
def get_all_clients():
    cur.execute('SELECT * FROM client')
    clients = cur.fetchall()
    return jsonify(clients)

@app.route("/client/<int:id>")
def get_client(id):
    cur.execute('SELECT * FROM client WHERE id = ?', (id,))
    client = cur.fetchone()
    if client:
        return jsonify(client)
    return jsonify({"error": "Client not found"}), 404

# Client order endpoints
@app.route("/client_order/all")
def get_all_client_orders():
    cur.execute('''
        SELECT 
            co.id,
            co.container_id,
            co.client_id,
            c.name as client_name,
            c.address as client_address,
            co.product_id,
            p.name as product_name,
            p.price as product_price,
            co.shipment_id,
            s.location_id,
            l.label as location_label,
            l.lat as location_lat,
            l.lon as location_lon,
            l.alt as location_alt,
            s.start_time,
            s.end_time,
            s.transport_type
        FROM client_order co
        JOIN client c ON co.client_id = c.id
        JOIN product p ON co.product_id = p.id
        JOIN shipment s ON co.shipment_id = s.id
        JOIN location l ON s.location_id = l.id
    ''')
    orders = cur.fetchall()
    return jsonify(orders)

@app.route("/client_order/<int:id>")
def get_client_order(id):
    cur.execute('''
        SELECT 
            co.id,
            co.container_id,
            co.client_id,
            c.name as client_name,
            c.address as client_address,
            co.product_id,
            p.name as product_name,
            p.price as product_price,
            co.shipment_id,
            s.location_id,
            l.label as location_label,
            l.lat as location_lat,
            l.lon as location_lon,
            l.alt as location_alt,
            s.start_time,
            s.end_time,
            s.transport_type
        FROM client_order co
        JOIN client c ON co.client_id = c.id
        JOIN product p ON co.product_id = p.id
        JOIN shipment s ON co.shipment_id = s.id
        JOIN location l ON s.location_id = l.id
        WHERE co.id = ?
    ''', (id,))
    order = cur.fetchone()
    if order:
        return jsonify(order)
    return jsonify({"error": "Client order not found"}), 404

# Report endpoints
@app.route("/report/all")
def get_all_reports():
    cur.execute('SELECT * FROM report')
    reports = cur.fetchall()
    return jsonify(reports)

@app.route("/report/<int:id>")
def get_report(id):
    cur.execute('SELECT * FROM report WHERE id = ?', (id,))
    report = cur.fetchone()
    if report:
        return jsonify(report)
    return jsonify({"error": "Report not found"}), 404



if __name__ == '__main__':
    # Change host to api.mod1.bit.gwep.dev for release/testing in release
    app.run(host='0.0.0.0', port=5001, debug=False)
