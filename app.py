from flask import Flask, jsonify, request
from datetime import datetime, timedelta
import sqlite3
import humanize
import waitress
import argparse
import seed
import utils
import locale

parser = argparse.ArgumentParser()
parser.add_argument("-d", "--dev", help="Run in Development mode", type=bool, action=argparse.BooleanOptionalAction)

seed.init_db()

locale.setlocale(locale.LC_ALL, 'de_DE.UTF-8')

con = sqlite3.connect('containers.db', check_same_thread=False)
cur = con.cursor()

app = Flask(__name__)

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

@app.route("/orders/new")
def new_shipment():
    today = datetime.today()
    shipment_type = request.args.get("type")
    arrival = None
    cost = None
    if shipment_type == 'Land':
        arrival = today + timedelta(days=5)
        cost = 10_000 * 5
    elif shipment_type == 'Sea':
        arrival = today + timedelta(weeks=2)
        cost = 1_000 * 14
    elif shipment_type == 'Air':
        arrival = today + timedelta(days=2)
        cost = 100_000 * 2
    return jsonify({
        "depart_date": utils.ordinal(int(today.strftime("%d"))),
        "depart_month": today.strftime("%B"),
        "arrival_date": utils.ordinal(int(arrival.strftime("%d"))) if arrival else "??",
        "arrival_month": arrival.strftime("%B") if arrival else "??",
        "cost": locale.currency(cost, grouping=True) if cost else "??"
    }), 200

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
        SELECT m.id, c.id, m.maintenance_type, m.status FROM maintenance m
        JOIN container c ON c.id=m.container_id
        WHERE m.id={maintenance_id}
    """)
    maintenance = cur.fetchone()
    return jsonify({
        "maintenance_id": maintenance[0],
        "container_id": maintenance[1],
        "maintenance_type": formatted_maintenance_type(maintenance[2]),
        "maintenance_status": maintenance[3]
    }), 200


if __name__ == '__main__':
    args = parser.parse_args()
    if args.dev:
        app.run(host='0.0.0.0', port=8080, debug=True)
    else:
        waitress.serve(app)