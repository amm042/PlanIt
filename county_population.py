import csv
from copy import copy
import sqlite3

conn = sqlite3.connect("data.db")

with open("CO-EST2015-alldata.csv") as f:
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
    if int(entry["STATE"]) == 42:
        name = entry["CTYNAME"].lower()
        population = int(entry["POPESTIMATE2015"])
        place = int(entry["COUNTY"])
        conn.execute("INSERT INTO PA_P VALUES (?, ?, ?);", (place, name, population,))

conn.commit()
conn.close()


