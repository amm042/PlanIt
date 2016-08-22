import tornado.ioloop
import tornado.web
import sqlite3
import json
import os
import subprocess
from threading import Timer
from geopy.distance import vincenty

from poly import populate
from splat import extract
from process import calculate_ber

class MainHandler(tornado.web.RequestHandler):
    def initialize(self):
        with open("index.html") as f:
            self.index = f.read()

    def get(self):
        self.write(self.index)

class QueryHandler(tornado.web.RequestHandler):
    def initialize(self, conn, ratio, tower_ratio):
        self.conn = conn
        self.ratio = ratio
        self.tower_ratio = tower_ratio

        self.radius = 1000000

    def get(self):
        c = self.conn.cursor()
        name = self.get_argument("name", "lewisburg")
        name = str(name).lower()
        
        tower = self.get_argument("tower", '{"lat": 40.9551497, "lng": -76.881709}')
        tower = json.loads(tower)
        tower = (tower["lat"], tower["lng"])
        
        query_string = "SELECT * FROM PA WHERE NAME='{name}';".format(name=name)
        c.execute(query_string)
        row = c.fetchone()
        if row is None or len(row) != 3: # try the county one
            query_string = "SELECT * FROM COUNTY WHERE NAME='{name}';".format(name=name)
            c.execute(query_string)
            row = c.fetchone()

        result = []
        if row is not None and len(row) == 3:
            place, name, coordinates = row
            c.execute("SELECT * FROM PA_P WHERE PLACE={place};".format(place=place))
            row_p = c.fetchone()
            if row_p is not None and len(row_p) == 3 and place!= 0:
                p, n, population = row_p
            else:
                population = -1

            if population == -1:
                # geoid does not match
                c.execute("SELECT * FROM PA_P WHERE NAME='{name}';".format(name=name))
                row_p = c.fetchone()
                if row_p is not None and len(row_p) == 3:
                    p, n, population = row_p

            coordinates = json.loads(coordinates)
            result = {"place": place, "name": name, "population": population, "coordinates": coordinates}

            # populate some porints
            points = populate(coordinates, population, self.ratio) 
            
            tower_points = populate(coordinates, population, self.tower_ratio)
            ## filter out the points
            #new_points = []
            #for point in points:
            #    p = (point[1], point[0])
            #    if vincenty(tower, p).meters < self.radius:
            #        new_points.append(point)
            result["points"] = points
            result["tower"] = tower_points
        self.write(json.dumps(result))


class SimulateHandler(tornado.web.RequestHandler):
    count = 0
    def post(self):
        data = tornado.escape.json_decode(self.request.body) 
        if "from" not in data or "to" not in data:
            self.write(json.dumps({}))
            return
        from_site = data["from"]
        to_site = data["to"]

        from_height = 120
        to_height = 5
        time_out = 20

        workspace = "workspace"

        if not os.path.exists(workspace):
            os.makedirs(workspace)

        from_qth = os.path.join(workspace, "{0}.qth".format(SimulateHandler.count))
        to_qth = os.path.join(workspace, "{0}.qth".format(SimulateHandler.count + 1))

        with open(from_qth, "w+") as f:
            lat = float(from_site["lat"])
            lng = abs(float(from_site["lng"]))
            write_data = "{0}\n{1}\n{2}\n{3}".format(str(SimulateHandler.count), lat, lng, from_height)
            f.write(write_data)
        SimulateHandler.count += 1
        with open(to_qth, "w+") as f:
            lat = float(to_site["lat"])
            lng = abs(float(to_site["lng"]))
            write_data = "{0}\n{1}\n{2}\n{3}".format(str(SimulateHandler.count), lat, lng, to_height)
            f.write(write_data)
        SimulateHandler.count += 1

        # call the python process

        args = ["splat", "-t", from_qth, "-r", to_qth]
        self.run(args, time_out)

        filename = str(SimulateHandler.count - 2) + "-to-" + str(SimulateHandler.count - 1) + ".txt"
        if not os.path.isfile(filename) or os.path.getsize(filename) == 0:
            self.write(json.dumps({}))
            return
        results = extract(filename)
        result = {}
        SNR, P = calculate_ber(results)
        result["snr"] = (SNR, P)
        result["lat"] = float(to_site["lat"])
        result["lng"] = float(to_site["lng"])
        result["index"] = data["index"]
        self.write(json.dumps(result))



    def run(self, cmd, timeout_sec):
        proc = subprocess.Popen(cmd, stdout=open(os.devnull, 'wb')) #, stderr=subprocess.PIPE)
        kill_proc = lambda p: p.kill()
        timer = Timer(timeout_sec, kill_proc, [proc])
        try:
            timer.start()
            stdout,stderr = proc.communicate()
        finally:
            timer.cancel()



class PlaceHandler(tornado.web.RequestHandler):
    NAMES = None
    def initialize(self, conn):
        if PlaceHandler.NAMES is None:
            c = conn.cursor()
            c.execute("SELECT NAME FROM PA;")
            PlaceHandler.NAMES= [x[0].title() for x in c.fetchall()]

            c.execute("SELECT NAME FROM COUNTY;")
            PlaceHandler.NAMES += [x[0].title() for x in c.fetchall()]

    def get(self):
        self.write(json.dumps(PlaceHandler.NAMES))


def delete_files():
    filelist = [ f for f in os.listdir(".") if f.endswith(".txt") ]
    for f in filelist:
        os.remove(f)

def make_app():
    delete_files()
    conn = sqlite3.connect("data.db")
    ratio = 0.05
    tower_ratio = 0.00005
    return tornado.web.Application([
        (r"/", MainHandler),
        (r'/static/(.*)', tornado.web.StaticFileHandler, {'path': "static"}),
        (r"/query", QueryHandler, dict(conn=conn, ratio=ratio, tower_ratio=tower_ratio)),
        ("/places.json", PlaceHandler, dict(conn=conn)),
        ("/simulate", SimulateHandler),
        ])

if __name__ == "__main__":
    app = make_app()
    app.listen(8887)
    tornado.ioloop.IOLoop.current().start()


