from flask import Flask, jsonify
import sqlite3
import humanize
import waitress
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("-d", "--dev", help="Run in Development mode", type=bool, action=argparse.BooleanOptionalAction)

con = sqlite3.connect('containers.db', check_same_thread=False)
cur = con.cursor()

app = Flask(__name__)

@app.route("/")
def hello_world():
    return "<p>Hello, Sucky !</p>"

@app.route("/shipments")
def get_shipments():
    cur.execute("""
        SELECT l.label, cl.name, c.id, s.start_time, s.end_time FROM shipment s
        JOIN location l ON l.id=s.location_id
        JOIN client_order o ON o.shipment_id=s.id
        JOIN container c ON c.id=o.container_id
        JOIN client cl ON cl.id=o.client_id
    """)
    shipments = cur.fetchall()
    formatted_shipments = []
    for shipment in shipments:
        formatted_shipments.append(
            {
                'mainText': shipment[0],
                'detailText': humanize.naturaltime(shipment[3]) + ' ' + '(' + shipment[2] + ')'

            }
        )
    return jsonify(formatted_shipments)

if __name__ == '__main__':
    args = parser.parse_args()
    if args.dev:
        app.run(host='0.0.0.0', port=8080, debug=True)
    else:
        waitress.serve(app)