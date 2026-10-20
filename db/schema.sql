-- CAZ-Route & Fleet Sync (Bristol) - PostgreSQL 16 + PostGIS 3 + pgRouting 3 reference schema (v0.1)
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgrouting;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ---------- Tenancy ----------
CREATE TABLE organisations (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name         text NOT NULL,
  org_type     text NOT NULL CHECK (org_type IN ('sole_trader','courier','retail','hospitality','hub_operator','bike_operator')),
  plan         text NOT NULL DEFAULT 'free' CHECK (plan IN ('free','solo','fleet','pro')),
  created_at   timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE users (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id       uuid NOT NULL REFERENCES organisations(id) ON DELETE CASCADE,
  email        text NOT NULL UNIQUE,
  role         text NOT NULL CHECK (role IN ('owner','dispatcher','driver','rider','hub_staff')),
  created_at   timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE vehicles (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id         uuid NOT NULL REFERENCES organisations(id) ON DELETE CASCADE,
  reg            text NOT NULL,
  vehicle_class  text NOT NULL CHECK (vehicle_class IN ('car','taxi','van','minibus','hgv','bus','coach','cargo_bike')),
  fuel           text NOT NULL CHECK (fuel IN ('diesel','petrol','electric','hydrogen','hybrid_petrol','hybrid_diesel','pedal')),
  euro_standard  smallint CHECK (euro_standard BETWEEN 1 AND 7),
  exempt         boolean NOT NULL DEFAULT false,
  last_checked   timestamptz,                 -- last DVLA / GOV.UK compliance lookup
  UNIQUE (org_id, reg)
);

-- ---------- Spatial reference data ----------
-- Official boundary imported from Bristol City Council open data; never hand-drawn.
CREATE TABLE caz_zone (
  id          serial PRIMARY KEY,
  name        text NOT NULL,
  valid_from  date NOT NULL,
  valid_to    date,
  geom        geometry(MultiPolygon, 4326) NOT NULL
);
CREATE INDEX caz_zone_gix ON caz_zone USING gist (geom);

-- Road/path network derived from OpenStreetMap (osm2pgrouting) with terrain attached.
CREATE TABLE road_edges (
  id            bigserial PRIMARY KEY,
  osm_id        bigint,
  source        bigint,
  target        bigint,
  geom          geometry(LineString, 4326) NOT NULL,
  length_m      double precision NOT NULL,
  highway       text,
  bike_only     boolean NOT NULL DEFAULT false,
  max_weight_t  numeric,
  elev_start_m  real,                       -- sampled from EA LIDAR composite DTM / OS Terrain
  elev_end_m    real,
  grade_pct     real GENERATED ALWAYS AS ((elev_end_m - elev_start_m) / NULLIF(length_m, 0) * 100.0) STORED,
  inside_caz    boolean NOT NULL DEFAULT false
);
CREATE INDEX road_edges_gix ON road_edges USING gist (geom);
CREATE INDEX road_edges_src ON road_edges (source);
CREATE INDEX road_edges_tgt ON road_edges (target);

-- Re-run after every CAZ boundary or network import.
CREATE OR REPLACE FUNCTION refresh_inside_caz() RETURNS void LANGUAGE sql AS $$
  UPDATE road_edges e SET inside_caz = EXISTS (
    SELECT 1 FROM caz_zone z
    WHERE z.valid_to IS NULL AND ST_Intersects(z.geom, e.geom));
$$;

-- Time-of-day congestion multipliers (A38 / M32 approaches, A4 Bath Road ...) learned from telemetry.
CREATE TABLE congestion_profiles (
  edge_id     bigint REFERENCES road_edges(id) ON DELETE CASCADE,
  dow         smallint NOT NULL CHECK (dow BETWEEN 0 AND 6),
  hour        smallint NOT NULL CHECK (hour BETWEEN 0 AND 23),
  multiplier  real NOT NULL CHECK (multiplier >= 1),
  PRIMARY KEY (edge_id, dow, hour)
);

-- ---------- Hubs & handshakes ----------
CREATE TABLE hubs (
  id                     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id                 uuid NOT NULL REFERENCES organisations(id),
  name                   text NOT NULL,
  geom                   geometry(Point, 4326) NOT NULL,
  capacity_parcels       integer NOT NULL CHECK (capacity_parcels > 0),
  bike_capacity_parcels  integer NOT NULL DEFAULT 12,
  opens                  time NOT NULL DEFAULT '07:00',
  closes                 time NOT NULL DEFAULT '19:00'
);
CREATE INDEX hubs_gix ON hubs USING gist (geom);

CREATE TABLE handshakes (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  hub_id          uuid NOT NULL REFERENCES hubs(id),
  sender_org_id   uuid NOT NULL REFERENCES organisations(id),
  bike_org_id     uuid REFERENCES organisations(id),
  van_vehicle_id  uuid REFERENCES vehicles(id),
  parcels         integer NOT NULL CHECK (parcels > 0),
  dest            geometry(Point, 4326) NOT NULL,
  state           text NOT NULL DEFAULT 'CREATED'
                  CHECK (state IN ('CREATED','VAN_ARRIVED','HANDED_OVER','OUT_FOR_DELIVERY','DELIVERED','FAILED','CANCELLED')),
  fee_gbp         numeric(8,2) NOT NULL,
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now()
);

-- ---------- Compliance ledger ----------
CREATE TABLE ledger_entries (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  vehicle_id  uuid NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
  travel_day  date NOT NULL,
  charge_gbp  numeric(8,2) NOT NULL CHECK (charge_gbp >= 0),
  source      text NOT NULL CHECK (source IN ('route_plan','telematics','manual','anpr_import')),
  paid_on     date,
  gov_receipt text,                                  -- reference from the GOV.UK payment, entered by user
  UNIQUE (vehicle_id, travel_day),                   -- daily charge applies once per vehicle per day
  CHECK (paid_on IS NULL OR paid_on BETWEEN travel_day - 6 AND travel_day + 6)
);

CREATE TABLE pcn_events (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  vehicle_id    uuid NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
  pcn_number    text NOT NULL,
  contravention date NOT NULL,
  served_on     date NOT NULL,
  amount_gbp    numeric(8,2) NOT NULL,
  status        text NOT NULL DEFAULT 'open' CHECK (status IN ('open','paid_discounted','paid_full','appealed','cancelled')),
  UNIQUE (pcn_number)
);

-- ---------- Marketplace ----------
CREATE TABLE drop_nodes (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  host_org_id      uuid NOT NULL REFERENCES organisations(id),
  name             text NOT NULL,
  geom             geometry(Point, 4326) NOT NULL,
  slots_per_day    integer NOT NULL CHECK (slots_per_day > 0),
  price_per_slot   numeric(6,2) NOT NULL CHECK (price_per_slot >= 0),
  active           boolean NOT NULL DEFAULT true
);
CREATE INDEX drop_nodes_gix ON drop_nodes USING gist (geom);

CREATE TABLE bookings (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  drop_node_id   uuid NOT NULL REFERENCES drop_nodes(id),
  booker_org_id  uuid NOT NULL REFERENCES organisations(id),
  booking_day    date NOT NULL,
  slots          integer NOT NULL CHECK (slots > 0),
  price_gbp      numeric(8,2) NOT NULL,
  created_at     timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX bookings_node_day ON bookings (drop_node_id, booking_day);

-- ---------- Example: grade-aware pgRouting cost for a cargo bike ----------
-- Cost in seconds; edges above 12% uphill are impassable (cost = -1 => excluded by pgr_dijkstra).
CREATE OR REPLACE FUNCTION bike_edges_sql() RETURNS text LANGUAGE sql IMMUTABLE AS $$
  SELECT $q$
    SELECT id, source, target,
      CASE WHEN grade_pct > 12 THEN -1
           ELSE length_m / (15.0/3.6 * GREATEST(0.3, 1 - 0.06 * GREATEST(grade_pct,0))) END AS cost,
      CASE WHEN -grade_pct > 12 THEN -1
           ELSE length_m / (15.0/3.6 * GREATEST(0.3, 1 - 0.06 * GREATEST(-grade_pct,0))) END AS reverse_cost
    FROM road_edges WHERE highway NOT IN ('motorway','motorway_link')
  $q$
$$;
-- usage: SELECT * FROM pgr_dijkstra(bike_edges_sql(), :src, :dst, directed => true);
