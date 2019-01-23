import json

with open("rsu_info.json","r") as rsu_file:
    data = json.load(rsu_file)
    print(data['rsu_list'][3])


