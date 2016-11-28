import requests


def get_elevation(lat, lon):
    r = requests.get(
        "http://localhost:5000/planit/elevation",
        params = {
            'key': 'eyJhbGciOiJIUzI1NiJ9.IjU4M2M3Y2EyNDdlZmE2MzgwMmI1NzNjOCI._fMAFEPDDGiAv9z6uhAKZVeBQx8TyCH1WzkzZzuXQew',
            'lat': lat,
            'lon': lon}
        )

    return r.json()['result']


for lon,lat in [    (-76.881249, 40.954899),
	                (-76.897619, 40.955291),
                    (-106.013942, 39.473847)]:
    print('{}, {} has elevation = {} meters'.format(
        lat,
        lon,
        get_elevation(lat,lon)))
