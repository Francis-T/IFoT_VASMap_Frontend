import requests
import json
import time
from flask import render_template, request
from ifot_vasmap import app

# SVC_WORKER_IP = '163.221.68.242'
SVC_WORKER_IP = 'pi-3'
SVC_WORKER_PORT = 5001
GET_AVE_SPD_API_URL = 'api/vas/get_average_speeds'
TASK_INFO_API_URL = 'api/task/{}/{}'
EXEC_TIME_INFO_API_URL = 'api/get_exec_time/{}'
RSU_LIST_INFO_API_URL = 'api/vas/request_rsu_list'

@app.route('/')
def index():
    return render_template("vasmap-test.html")

@app.route('/get_rsu_list', methods=['GET'])
def get_rsu_list():
    resp = request_rsu_list()
    return resp.text, 200

@app.route('/get_exec_time/<unique_id>', methods=['GET'])
def get_exec_time(unique_id):
    resp = request_exec_time_info(int(unique_id))
    return resp.text, 200

@app.route('/get_ave_speed_data', methods=['POST'])
def get_ave_speed_data():
    rsu_list = json.loads(request.form['rsu_list'])

    start_time = 0
    if 'start_time' in request.form:
        start_time = int(request.form['start_time'])
    
    end_time = time.time()
    if 'end_time' in request.form:
        end_time = int(request.form['end_time'])

    print(rsu_list)

    resp = request_average_speeds(start_time, end_time, rsu_list)
    json_resp = json.loads(resp.text)
    task_ids = json_resp['response_object']['data']['task_id']

    done = False
    agg_task_id = ''
    while not done:
        for task_id in task_ids:
            resp = json.loads(request_task_info(task_id, 'default').text)
            if resp['data']['task_status'] != 'finished':
                print(".", end='')
                continue

            metas = resp['data']['task_result']['metas']
            task_count = metas['task_count']
            done_count = metas['done_task_count']

            if task_count == done_count:
                print("  Aggregator Task Id : {}".format(metas['agg_task_id']))
                agg_task_id = metas['agg_task_id']
                done = True

    done = False
    while not done:
        resp = request_task_info(agg_task_id, 'aggregator')
        json_resp = json.loads(resp.text)
        status = json_resp['data']['task_status']
        if status == 'finished':
            done = True

    if json_resp['status'] != 'success':
        return { 'error' : 'Aggregation failed' }, 500

    results = {
        "unique_id" : json_resp['data']['task_result']['unique_id'],
        "data" : json_resp['data']['task_result']['result'],
    }

    return json.dumps(results), 200

#########################################################################
##
##  Utility Functions
##
#########################################################################
def send_request(api_url, host, port, payload=None):
    request_url =  "http://{}:{}/{}"
    request_url = request_url.format(host, port, api_url)
    response = requests.get(request_url, data=payload)
    print(response.text)
    return response

def request_average_speeds(start, end, rsu_list):
    payload = {
        'influx_ip' : '163.221.68.206',
        'rsu_list' : rsu_list,
        'start_time' : int(start),
        'end_time' : int(end),
    }
    return send_request(GET_AVE_SPD_API_URL, SVC_WORKER_IP, SVC_WORKER_PORT, payload=json.dumps(payload))

def request_task_info(task_id, task_queue):
    task_info_url = TASK_INFO_API_URL.format(task_queue, task_id)
    return send_request(task_info_url, SVC_WORKER_IP, SVC_WORKER_PORT)

def request_exec_time_info(unique_id):
    exec_time_info_url = EXEC_TIME_INFO_API_URL.format(unique_id)
    return send_request(exec_time_info_url, SVC_WORKER_IP, SVC_WORKER_PORT)

def request_rsu_list():
    return send_request(RSU_LIST_INFO_API_URL, SVC_WORKER_IP, SVC_WORKER_PORT)


