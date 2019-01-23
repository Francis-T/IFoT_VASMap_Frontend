import json

def calculate(y1, y2, x1, x2, div):
    y_b = y1 - y2
    x_b = x1 - x2

    coords = []
    for i in range(0, div+1):
        y = y2 + i * (y_b / float(div))

        for j in range(0, div+1):
            x = x2 + j * (x_b / float(div))

            coords.append((x, y))

    idx = 1
    locs = []
    for c in coords:
        # print("RSU{:04d}, {}, {}".format(idx, l[0], l[1]))
        loc = {
            'rsu_id' : 'RSU{:04d}'.format(idx),
            'lon' : c[0],
            'lat' : c[1],
        }

        locs.append( loc )
        idx += 1

    return locs

if __name__ == "__main__":
    locs = calculate(36.096399, 36.233539, -86.662728, -86.883471, 4)
    print(json.dumps( { "rsu_list" : locs } ))


