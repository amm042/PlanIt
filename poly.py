import matplotlib.path as mplPath
import random

def populate(points, population, ratio):
    path = mplPath.Path(points)

    x_max = max(points, key=lambda x:x[0])[0]
    x_min = min(points, key=lambda x: x[0])[0]
    y_max = max(points, key=lambda x:x[1])[1]
    y_min = min(points, key=lambda x:x[1])[1]

    area = (y_max - y_min) * (x_max - x_min)
    needed = int(population * ratio)
    if needed < 0:
        needed = 0
    result = []
    while len(result) < needed:
        x = random.uniform(x_min, x_max)
        y = random.uniform(y_min, y_max)
        if path.contains_point((x, y)):
            result.append((x, y))
    return result 

