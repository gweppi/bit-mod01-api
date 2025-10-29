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

@app.route("/shipments")
def get_shipments():
    cur.execute('SELECT l.label, s.start_time, s.end_time FROM shipment s JOIN location l ON l.id=s.location_id')
    shipments = cur.fetchall()
    return jsonify(shipments)

if __name__ == '__main__':
    # Change host to api.mod1.bit.gwep.dev for release/testing in release
    app.run(host='0.0.0.0', port=5001, debug=False)
