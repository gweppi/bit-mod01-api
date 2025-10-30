from datetime import datetime, timedelta
import sqlite3
import random
import os

def init_db(override: bool = False):
   if not os.path.exists('containers.db') or override:
      print("Initializing db...")
      
      con = sqlite3.connect('containers.db')
      cur = con.cursor()

      # Creates the tables in the DB
      with open('scripts/create_tables.sql', 'r') as f:
         create_tables_script = f.read()
      cur.executescript(create_tables_script)

      # Seed DB
      # =======
      # Location data
      location_data = [
         (1, 'Rotterdam', 51.885, 4.286, 2),
         (2, 'Enschede', 52.21833,6.89583, 45),
         (3, 'Eindhoven', 51.4416, 5.4697, 23)
      ]
      cur.executemany('INSERT INTO location (id, label, lat, lon, alt) VALUES (?,?,?,?,?)', location_data)
      # Shipment data
      shipment_status_options = [
         'Container has been marked for retour',
         'Cleared inspection',
         'Getting ready for shipment'
      ]
      shipment_data = [
         (1, 1, 1743590400, datetime.now().timestamp() + timedelta(weeks=1).total_seconds(), 'sea', random.choice(shipment_status_options)),
         (2, 1, 1746384000, datetime.now().timestamp() + timedelta(weeks=2).total_seconds(), 'air', random.choice(shipment_status_options)),
         (3, 2, 1749331200, datetime.now().timestamp() + timedelta(weeks=3).total_seconds(), 'land', random.choice(shipment_status_options)),
         (4, 3, 1750646400, datetime.now().timestamp() + timedelta(weeks=4).total_seconds(), 'land', random.choice(shipment_status_options)),
      ]
      cur.executemany('INSERT INTO shipment (id, location_id, start_time, end_time, transport_type, status) VALUES (?,?,?,?,?,?)', shipment_data)
      # Container meta data
      length_options = [5,10,15,20,25]
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
         for i in range(1,6)
      ]
      cur.executemany('INSERT INTO container_meta_data (id, length, height, width, volume, weight) VALUES (?,?,?,?,?,?)', container_meta_data)
      # Container data
      container_data = [
         (
            'ASML ' + str(random.randint(10000, 99999)) + ' 4',
            random.randint(1, 3),
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
      # Maintenance
      maintenance_data = [
         (
            i,
            random.choice(container_data)[0],
            random.choice(['outer_repair', 'deepclean']),
            random.choice(['maintenance_scheduled', 'quality control', 'started maintenance', 'finished maintenance'])
         )
         for i in range(1,6)
      ]
      cur.executemany('INSERT INTO maintenance (id, container_id, maintenance_type, status) VALUES (?,?,?,?)', maintenance_data)
      # Close up connection
      con.commit()
      cur.close()
      con.close()

      print('Done initialzing db')

if __name__ == '__main__':
   init_db(override=True)