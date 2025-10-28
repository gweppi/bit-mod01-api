from flask import Flask, jsonify
import sqlite3

con = sqlite3.connect('containers.db', check_same_thread=False)
cur = con.cursor()

app = Flask(__name__)

@app.route("/")
def hello_world():
    return "<p>Hello, Sucky !</p>"

@app.route("/shipments")
def get_shipments():
    cur.execute('SELECT l.label, s.start_time, s.end_time FROM shipments s JOIN locations l ON l.id=s.location_id')
    shipments = cur.fetchall()
    return jsonify(shipments)