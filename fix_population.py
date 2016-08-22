import sqlite3

conn = sqlite3.connect("data.db")
places = [
        {
            "place": 50552,
            "name": "montandon",
            "population": 903
            },
        {
            "place": 80144,
            "name": "vicksburg",
            "population": 261
            },
        {
            "place": 43704,
            "name": "linntown",
            "population": 1489
            },
        {
            "place": 40432,
            "name": "kratzerville",
            "population": 391
            },



        ]



for entry in places:
    place = entry["place"]
    population = entry["population"]
    name = entry["name"].lower()
    conn.execute("INSERT INTO PA_P VALUES (?, ?, ?);", (place, name, population,))

conn.commit()
conn.close()
