from bs4 import BeautifulSoup
import sqlite3
import json
import csv
from copy import copy


conn = sqlite3.connect("data.db")
conn.execute("CREATE TABLE IF NOT EXISTS PA (PLACE INT UNIQUE, NAME TEXT, COORDINATES TEXT);")

with open("cb_2015_42_place_500k.kml") as f:
    soup = BeautifulSoup(f, 'xml')
    lst = list(soup.find_all("Placemark"))

for entry in lst:
    name = ""
    total_area = 0
    place = 0
    for data in entry.find_all("SimpleData"):
        if data["name"] == "NAME":
            name = str(data.string).lower()
        elif data["name"] == "ALAND":
            total_area = int(data.string)
        elif data["name"] == "PLACEFP":
            place = int(data.string)
    raw_coordinates = entry.find("coordinates").string
    coordinates = [x.split(",")[:2] for x in raw_coordinates.split(" ") if len(x) > 0]
    coordinates = [(float(x), float(y)) for (x, y) in coordinates]
    conn.execute("INSERT INTO PA VALUES (?, ?, ?)", (place, name, json.dumps(coordinates)))

conn.commit()

# load population file
conn.execute("CREATE TABLE IF NOT EXISTS PA_P (PLACE INT, NAME TEXT, POPULATION INT);")

with open("SUB-EST2015_42.csv") as f:
    reader = csv.reader(f)
    count = 0
    population_result = []
    header = []
    for row in reader:
        if count == 0:
            header = copy(row)
            count += 1
            continue
        entry = {}
        for i in range(len(header)):
            entry[header[i]] = row[i]

        population_result.append(entry)
        count += 1

for entry in population_result:
    place = entry["PLACE"]
    population = entry["POPESTIMATE2015"]
    name = entry["NAME"].lower()
    name = name.replace("borough", "").strip()
    conn.execute("INSERT INTO PA_P VALUES (?, ?, ?);", (place, name, population,))

conn.commit()
conn.close()
