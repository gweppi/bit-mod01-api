from flask import Flask, jsonify
import sqlite3
import humanize
import waitress
import argparse
import time
import seed

parser = argparse.ArgumentParser()
parser.add_argument("-d", "--dev", help="Run in Development mode", type=bool, action=argparse.BooleanOptionalAction)

seed.init_db()

con = sqlite3.connect('containers.db', check_same_thread=False)
cur = con.cursor()

app = Flask(__name__)

@app.route("/")
def hello_world():
    return "<p>Hello, BIT!</p>"

@app.route("/shipments")
def get_shipments():
    cur.execute("""
        SELECT l.label, cl.name, o.id, s.start_time, s.end_time FROM shipment s
        JOIN location l ON l.id=s.location_id
        JOIN client_order o ON o.shipment_id=s.id
        JOIN container c ON c.id=o.container_id
        JOIN client cl ON cl.id=o.client_id
    """)
    shipments = cur.fetchall()
    formatted_shipments = []
    for shipment in shipments:
        current_time = time.time()
        shipment_start_time = shipment[3]
        shipement_end_time = shipment[4]
        if current_time > shipment_start_time:
            # Shipment is currently underway
            shipment_string = 'package arrives in ' + humanize.naturaltime(shipement_end_time)
        else:
            shipment_string = 'package leaves location in ' + humanize.naturaltime(shipment_start_time)
        formatted_shipments.append(
            {
                'mainText': 'Shipment to ' + shipment[0] + ' shipping order ' + str(shipment[2]),
                'detailText': shipment_string,
                'nextScreenStartValue': shipment[2]
            }
        )
    return jsonify(formatted_shipments), 200

@app.route("/shipments/<string:shipment_id>")
def get_shipment_by_id(shipment_id):
    cur.execute(f"""
        SELECT c.id, l.label, l.lat, l.lon, s.start_time, s.end_time, s.transport_type FROM shipment s
        JOIN location l ON l.id=s.location_id
        JOIN client_order o ON o.shipment_id=s.id
        JOIN container c ON c.id=o.container_id
        WHERE s.id={shipment_id}
    """)
    shipment = cur.fetchone()
    if not shipment:
        return "No shipment with that ID found", 404
    return jsonify({
        "container_id": shipment[0],
        "lat": shipment[1],
        "lon": shipment[2],
        "start_time": shipment[3],
        "end_time": shipment[4],
        "transport_type": shipment[5]
    }), 200

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
            'detailText': f'Arrives in {humanize.naturaltime(order[2])} from {order[3]}',
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

if __name__ == '__main__':
    args = parser.parse_args()
    if args.dev:
        app.run(host='0.0.0.0', port=8080, debug=True)
    else:
        waitress.serve(app)