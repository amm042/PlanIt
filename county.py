from bs4 import BeautifulSoup
import sqlite3
import json
import csv
from copy import copy


conn = sqlite3.connect("data.db")
conn.execute("CREATE TABLE IF NOT EXISTS COUNTY (PLACE INT, NAME TEXT, COORDINATES TEXT);")

with open("cb_2015_us_county_500k.kml") as f:
    soup = BeautifulSoup(f, 'xml')
    lst = list(soup.find_all("Placemark"))

count = 0
for entry in lst:
    name = ""
    total_area = 0
    place = 0
    state = 0
    for data in entry.find_all("SimpleData"):
        if data["name"] == "NAME":
            name = str(data.string).lower() + " county"
        elif data["name"] == "ALAND":
            total_area = int(data.string)
        elif data["name"] == "PLACEFP":
            place = int(data.string)
        elif data["name"] == "STATEFP":
            state = int(data.string)
    if state != 42:
        continue
    else:
        count += 1
    raw_coordinates = entry.find("coordinates").string
    coordinates = [x.split(",")[:2] for x in raw_coordinates.split(" ") if len(x) > 0]
    coordinates = [(float(x), float(y)) for (x, y) in coordinates]
    conn.execute("INSERT INTO COUNTY VALUES (?, ?, ?)", (place, name, json.dumps(coordinates)))

conn.commit()
conn.close()

print("county count", count)
