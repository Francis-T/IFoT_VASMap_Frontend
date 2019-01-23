import requests
import json
import time
import random

RSU_LIST = []

VALID_STARTS = ["RSU"]
FREQUENCY = 0.100
TIME_ADJUSTMENT = 1000000000

class Car():
    def __init__(self):
        self.id = int(time.time() * 1000)
        self.rsu_id = None
        self.lat = 0.0
        self.lon = 0.0
        self.speed = 0.0
        self.direction = 0.0 # 0 = EAST, 90 = NORTH, 180 = WEST, 270 = SOUTH
        self.path = []

        return

    def run(self):
        rsu_idx = random.randint(0, len(RSU_LIST))
        rsu = RSU_LIST[rsu_idx - 1]
        self.rsu_id = rsu['rsu_id']
        self.lat = rsu['lat']
        self.lon = rsu['lon']
        self.speed = 10.0 + (random.random() * 90.0)
        self.direction = random.choice([350.0, 85.0, 170.0, 260.0])

        time.sleep(random.random() * FREQUENCY)

        return self

    def __repr__(self):
        return "{} ({}): lat={}, lng={}, spd={}, dir={}".format(self.id, self.rsu_id, self.lat, self.lon, self.speed, self.direction)


class InfluxDB():
    def __init__(self, url='http://163.221.68.206:8086', name='default'):
        self.db_url = url
        self.query_url = "{}/query".format(self.db_url)
        self.write_url = "{}/write".format(self.db_url)
        self.db_name   = name
        self.retention_policy = "default_rp"

        return

    def set_retention_policy(self, duration="60d", replication=1):
        query = "CREATE RETENTION POLICY {} ON {} DURATION {} REPLICATION {}" 
        query = query.format(self.retention_policy, self.db_name, duration, replication)
        payload = {
            "pretty": True,
            "epoch": 'ms',
            "q": query
        }
        return requests.post(self.query_url, data=payload)


    def get_retention_policies(self):
        query = "SHOW RETENTION POLICIES ON {};".format(self.db_name)
        payload = {
            "pretty": True,
            "epoch": 'ms',
            "q": query
        }

        return requests.get(self.query_url, params=payload)

    def get_databases(self):
        query = "SHOW DATABASES;"
        payload = {
            "pretty": True,
            "epoch": 'ms',
            "q": query
        }

        resp = requests.get(self.query_url, params=payload)
        temp_list = json.loads(resp.text)['results'][0]['series'][0]['values']

        return [ db[0] for db in temp_list ]

    def create(self, db_name=None):
        if db_name != None:
            self.db_name = db_name

        query = "CREATE DATABASE {};".format(self.db_name)
        payload = {
            "pretty": True,
            "epoch": 'ms',
            "q": query
        }
        return requests.post(self.query_url, data=payload)

    def drop(self):
        query = "DROP DATABASE {};".format(self.db_name)
        payload = {
            "pretty": True,
            "epoch": 'ms',
            "q": query
        }
        return requests.post(self.query_url, data=payload)

    def write(self, car_id, rsu_id, speed, lat, lng, direction):
        params = {
            "db" : self.db_name,
            "rp" : self.retention_policy,
        }
        payload = 'rsu_data car_id="{}",rsu_id="{}",lat={},lng={},speed={},direction={}'
        payload = payload.format(car_id, rsu_id, lat, lng, speed, direction)

        return requests.post(self.write_url, params=params, data=payload)

    def query(self, fields, meas, start=None, end=None):
        # Build the filter clause
        where = ""
        if (start != None) and (end != None):
            if int(start) < TIME_ADJUSTMENT ** 2:
                start = int(start) * TIME_ADJUSTMENT

            if int(end) < TIME_ADJUSTMENT ** 2:
                end = int(end) * TIME_ADJUSTMENT

            where = "WHERE time >= {} AND time <= {} AND rsu_id = 'RSU_1'".format(start, end)

        # Build the rest of the query
        query = 'SELECT {} from "{}"."{}".{} {};'
        query = query.format(fields, self.db_name, self.retention_policy, meas, where)

        payload = {
            "db": self.db_name,
            "pretty": True,
            "epoch": 'ms',
            "q": query
        }

        print(query)
        resp = requests.get(self.query_url, params=payload)
        resp = json.loads(resp.text)

        results = resp['results'][0]['series'][0]
        return results

db = InfluxDB(name='VASMAP')
 
db_list = db.get_databases()
if not 'VASMAP' in db_list:
    resp = db.create()
    resp = db.set_retention_policy()

# resp = db.write(435, 60.0, 14.37, 120.58, 0.0)
# 
# resp = db.query("*", "rsu_data")
# print(resp)
# 
# resp = db.drop()
# resp = db.get_databases()
# print(resp)

with open("rsu_info.json","r") as rsu_json_file:
    data = json.load(rsu_json_file)
    RSU_LIST = data['rsu_list']

for i in range(0, 1000):
    car = Car().run()
    print("{}, {}, {}, {}, {}, {}".format(car.id, car.rsu_id, car.speed, car.lat, car.lon, car.direction))
    resp = db.write(car.id, car.rsu_id, car.speed, car.lat, car.lon, car.direction)

# resp = db.query("*", "rsu_data", start=0, end=int(time.time()))
# print(resp)

# resp = db.drop()
# resp = db.get_databases()

