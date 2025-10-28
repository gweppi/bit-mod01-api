CREATE TABLE IF NOT EXISTS location (
   id integer PRIMARY KEY,
   label text,
   lat real,
   lon real,
   alt integer
);

CREATE TABLE IF NOT EXISTS shipment (
   id integer PRIMARY KEY,
   location_id integer REFERENCES location(id),
   start_time integer,
   end_time integer,
   transport_type text -- either SEA, AIR, LAND
);

CREATE TABLE IF NOT EXISTS container (
   id text PRIMARY KEY,
   location_id integer REFERENCES location(id),
   meta_data_id integer REFERENCES container_meta_data(id),
   cycle_count integer
);

CREATE TABLE IF NOT EXISTS container_meta_data ( -- All sizes in m, volume in m^3, weight in kg
   id integer PRIMARY KEY,
   length real,
   height real,
   width real,
   volume real,
   weight real
);

CREATE TABLE IF NOT EXISTS product (
   id integer PRIMARY KEY,
   name text,
   price integer -- in euros
);

CREATE TABLE IF NOT EXISTS client (
   id integer PRIMARY KEY,
   name text,
   address text
);

CREATE TABLE IF NOT EXISTS client_order (
   id integer PRIMARY KEY,
   container_id text REFERENCES container(id),
   product_id integer REFERENCES product(id),
   shipment_id integer REFERENCES shipment(id),
   client_id integer REFERENCES client(id)
);

CREATE TABLE IF NOT EXISTS report (
   id integer PRIMARY KEY,
   container_id text REFERENCES container(id),
   type text, -- either MAINTENANCE or INSPECTION
   status text,
   cost integer, -- in cents
   file_name text -- the name of the file containing the actual report
);