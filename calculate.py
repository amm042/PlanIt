from splat import extract
import os
import json


exist_count = 0
i = 0
results = []
while  exist_count < 4:
    filename = str(i) + "-to-" + str(i+1) + ".txt"
    if os.path.isfile(filename):
        entry = extract(filename)
        if entry is None:
            i += 2
            continue
        results.append(entry)
        exist_count = 0
    else:
        exist_count += 1
    i += 2

print(len(results))
with open("data.json", "w+") as f:
    json.dump(results, f)
    print("file dumped")
