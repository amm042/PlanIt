def extract(filename):
    result = {}
    site_name = filename.replace(".txt", "")
    site_name = site_name.split("to-")[-1]    
    with open(filename, "rb") as f:
        lines = f.read().decode("iso-8859-1").split("\n")
        start = False
        last_entry = None
        for line in lines:
            if not start:
                if "Summary For The Link Between" in line:
                    start =  True
                else:
                    continue
            else:
                if len(line.strip()) > 0:
                    if "---" in line:
                        return result
                    line_values = line.split(":")
                    if len(line_values) == 1 and last_entry is not None:
                        del result[entry]
                        return result
                    entry, value = line_values
                    entry = entry.replace("at", "").replace(site_name, "").strip()
                    result[entry] = value.strip()
                    last_entry = entry


