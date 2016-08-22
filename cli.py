import sqlite3
import json
import os
import subprocess
from threading import Timer
from threading import Lock
import multiprocessing as mp
import time


from poly import populate
from splat import extract
from process import calculate_ber

class BaseClass:
    def __init__(self, arg):
        self.arg = arg

    def get_argument(self, name, default_value):
        if name not in self.arg:
            return default_value
        else:
            return self.arg[name]

class QueryHandler:
    def __init__(self, conn, ratio, tower_ratio):
        self.conn = conn
        self.ratio = ratio
        self.tower_ratio = tower_ratio
        self.radius = 1000000



    def get(self, name):
        c = self.conn.cursor()
        name = str(name).lower()
        
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
        return result


class SimulateHandler:
    count = 0
    lock = Lock()

    def get(self, data):
        if "from" not in data or "to" not in data:
            return {}
        from_site = data["from"]
        to_site = data["to"]

        from_height = 120
        to_height = 5
        time_out = 20

        workspace = "workspace"

        if not os.path.exists(workspace):
            os.makedirs(workspace)

        SimulateHandler.lock.acquire()
        from_qth = os.path.join(workspace, "{0}.qth".format(SimulateHandler.count))
        to_qth = os.path.join(workspace, "{0}.qth".format(SimulateHandler.count + 1))
        SimulateHandler.count += 2
    
        with open(from_qth, "w+") as f:
            lat = float(from_site["lat"])
            lng = abs(float(from_site["lng"]))
            write_data = "{0}\n{1}\n{2}\n{3}".format(str(SimulateHandler.count - 2), lat, lng, from_height)
            f.write(write_data)
        with open(to_qth, "w+") as f:
            lat = float(to_site["lat"])
            lng = abs(float(to_site["lng"]))
            write_data = "{0}\n{1}\n{2}\n{3}".format(str(SimulateHandler.count - 1), lat, lng, to_height)
            f.write(write_data)

        SimulateHandler.lock.release()
        # call the python process

        args = ["splat", "-t", from_qth, "-r", to_qth]
        self.run(args, time_out)
        
        time.sleep(0.05)

        SimulateHandler.lock.acquire()
        filename = str(SimulateHandler.count - 2) + "-to-" + str(SimulateHandler.count - 1) + ".txt"
        SimulateHandler.lock.release()
        
        if not os.path.isfile(filename) or os.path.getsize(filename) == 0:
            # print("it's wrong here", filename)
            return {}
        results = extract(filename)
        result = {}
        SNR, P = calculate_ber(results)
        result["snr"] = SNR
        result["lat"] = float(to_site["lat"])
        result["lng"] = float(to_site["lng"])
        # print(result)
        return result



    def run(self, cmd, timeout_sec):
        proc = subprocess.Popen(cmd, stdout=open(os.devnull, 'wb')) #, stderr=subprocess.PIPE)
        kill_proc = lambda p: p.kill()
        timer = Timer(timeout_sec, kill_proc, [proc])
        try:
            timer.start()
            stdout,stderr = proc.communicate()
        finally:
            timer.cancel()



class PlaceHandler(BaseClass):
    NAMES = None
    def __init__(self, conn):
        if PlaceHandler.NAMES is None:
            c = conn.cursor()
            c.execute("SELECT NAME FROM PA;")
            PlaceHandler.NAMES= [x[0].title() for x in c.fetchall()]

            c.execute("SELECT NAME FROM COUNTY;")
            PlaceHandler.NAMES += [x[0].title() for x in c.fetchall()]

        super().__init__()

    def get(self):
        self.write(json.dumps(PlaceHandler.NAMES))


def delete_files():
    filelist = [ f for f in os.listdir(".") if f.endswith(".txt") ]
    for f in filelist:
        os.remove(f)


def calculate(arg):
    try:
        data_point, tower_list, result_points, s = arg
        snr_points = []
        for tower in tower_list:
            from_site = {"lng": tower[0], "lat":tower[1]}
            to_site = {"lng": data_point[0], "lat": data_point[1]}

            snr = s.get({"from": from_site, "to": to_site})#["snr"][0]
            if len(snr) > 0:
                snr_points.append(snr)
        if len(snr_points) == 0:
            # print("it's wrong here")
            return {"error": True}
        m_snr = snr_points[0]
        for entry in snr_points:
            if entry["snr"] > m_snr["snr"]:
                m_snr = entry
        # print("max is", m_snr)
        return m_snr
    except Exception as ex:
        print(ex)
        return {"error": True}




def main():
    delete_files()
    conn = sqlite3.connect("data.db")
    ratio = 0.010
    tower_ratio = 0.0000429
    q = QueryHandler(conn, ratio, tower_ratio)
    s = SimulateHandler()
    points = []
    tower_list = []
    location_list = ["Union County", "Northumberland County", "Snyder County"]
    for location in location_list:
        result = q.get(location)
        tower_list += result["tower"]
        points += result["points"]
        print(len(points), len(tower_list))

    # compute site
    result_points = []
    
    args = [(point, tower_list, result_points, s) for point in points if point is not None]
    
    pool =  mp.Pool(mp.cpu_count() // 2)
    result_points = pool.map(calculate, args)
    results = [entry for entry in result_points if "error" not in entry]
    with open("snr.json", "w+") as f:
        json.dump({"snr": results, "tower": tower_list}, f)


if __name__ == "__main__":
    main()

