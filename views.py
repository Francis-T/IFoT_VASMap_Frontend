from flask import render_template, jsonify, request, current_app, Blueprint
from flask import send_from_directory, url_for, redirect
from werkzeug.utils import secure_filename
from ..models.models import Node
from ..forms.upload_form import UploadForm
from rq import Queue, Connection
import redis
import os
import json
from rq.registry import StartedJobRegistry, FinishedJobRegistry
import urllib.request, json 
import requests

from bs4 import BeautifulSoup

from ..forms.upload_form import TextForm, Nuts2Form

from ..main import funcs
import numpy as np

import os
import csv
import time
import datetime
from dateutil import tz

import multiprocessing

NODE_COUNT      = '_node_count'
DONE_NODE_COUNT = '_done_node_count'
TASK_COUNT      = '_task_count'
DONE_TASK_COUNT = '_done_task_count'
EXEC_TIME_INFO  = 'exec_time_info'

api = Blueprint('api', __name__,)

feat_name_list = [
    "acc_x", "acc_y", "acc_z", "acc_comp",
    "lacc_x", "lacc_y", "lacc_z", "lacc_comp",
    "gra_x", "gra_y", "gra_z", "gra_comp",
    "gyr_x", "gyr_y", "gyr_z", "gyr_comp",
    "mag_x", "mag_y", "mag_z", "mag_comp",
    "ori_w", "ori_x", "ori_y", "ori_z", "pre"]

@api.route('/', methods=['GET'])
def home():
  return "{'hello':'world'}"

def get_all_finished_tasks_from(queue_name):
    with Connection(redis.from_url(current_app.config['REDIS_URL'])):
      # q = Queue(queue_name)
      f_registry = FinishedJobRegistry(queue_name)
      data = {}

      finished_job_ids = f_registry.get_job_ids()
      data['status'] = 'success'
      data['queue_name'] = queue_name
      data['finished'] = {}

      data['finished']['count'] = len(finished_job_ids)
      data['finished']['finished_tasks_ids'] = []
      for finished_job_id in finished_job_ids:
        data['finished']['finished_tasks_ids'].append(finished_job_id)

      return jsonify(data)

def get_all_queued_tasks_from(queue_name):
    with Connection(redis.from_url(current_app.config['REDIS_URL'])):
      q = Queue(queue_name)
      queued_job_ids = q.job_ids
      data = {}

      data['status'] = 'success'
      data['queue_name'] = queue_name
      data['queued'] = {}

      data['queued']['count'] = len(queued_job_ids)
      data['queued']['queued_tasks_ids'] = []
      for queued_job_id in queued_job_ids:
        data['queued']['queued_tasks_ids'].append(queued_job_id)

      return jsonify(data)

def get_all_running_tasks_from(queue_name):
    with Connection(redis.from_url(current_app.config['REDIS_URL'])):
      # q = Queue(queue_name)
      registry = StartedJobRegistry(queue_name)
      data = {}

      running_job_ids = registry.get_job_ids()
      data['status'] = 'success'
      data['queue_name'] = queue_name
      data['running'] = {}

      data['running']['count'] = len(running_job_ids)
      data['running']['running_tasks_ids'] = []
      for running_job_id in running_job_ids:
        data['running']['running_tasks_ids'].append(running_job_id)

      return jsonify(data)

def getalltasksID():
  with Connection(redis.from_url(current_app.config['REDIS_URL'])):
    q = Queue('default')
    registry = StartedJobRegistry('default')
    f_registry = FinishedJobRegistry('default')
  if q:
    data = {}
    running_job_ids = registry.get_job_ids()
    expired_job_ids = registry.get_expired_job_ids()
    finished_job_ids = f_registry.get_job_ids()
    queued_job_ids = q.job_ids
    data['status'] = 'success'
    data['queue_name'] = 'default' #Make dynamic or parameterized?
    data['running'] = {}
    data['queued'] = {}
    data['expired'] = {}
    data['finished'] = {}

    data['running']['count'] = len(running_job_ids)
    data['running']['running_tasks_ids'] = []
    for running_job_id in running_job_ids:
      data['running']['running_tasks_ids'].append(running_job_id)

    data['queued']['count'] = len(queued_job_ids)
    data['queued']['queued_tasks_ids'] = []
    for queued_job_id in queued_job_ids:
      data['queued']['queued_tasks_ids'].append(queued_job_id)

    data['expired']['count'] = len(expired_job_ids)
    data['expired']['expired_tasks_ids'] = []
    for expired_job_id in expired_job_ids:
      data['expired']['expired_tasks_ids'].append(expired_job_id)

    data['finished']['count'] = len(finished_job_ids)
    data['finished']['finished_tasks_ids'] = []
    for finished_job_id in finished_job_ids:
      data['finished']['finished_tasks_ids'].append(finished_job_id)

    return jsonify(data)
  else:
    return jsonify({'status': 'error'})

@api.route('/getallqueues', methods=['POST'])
def getallqeueues():
    return getalltasksID()

def get_task_status(queue, task_id):
  with Connection(redis.from_url(current_app.config['REDIS_URL'])):
    q = Queue(queue)
    task = q.fetch_job(task_id)
  if task is not None:
    response_object = {
      'status': 'success',
      'data': {
          'task_id': task.get_id(),
          'task_status': task.get_status(),
          'task_result': task.result,
      }
    }
  else:
    response_object = {'status': 'error, task is None'}
  return jsonify(response_object)

@api.route('/getqueuecount', methods=['POST'])
def getqueuecount():
  with Connection(redis.from_url(current_app.config['REDIS_URL'])):
    q = Queue()
  if q:
    return jsonify({'length': len(q)})
  else:
    return jsonify({'length': -1})

@api.route('/checkqueue', methods=['GET', 'POST'])
def checkqueue():
  with Connection(redis.from_url(current_app.config['REDIS_URL'])):
    q = Queue()
  if q:
    data = {}
    data['status'] = 'success'
    data['jobs_count'] = len(q)
    data['jobs'] = []
    for job_id in q.job_ids:
      job = q.fetch_job(job_id)
      task_status = job.get_status()
      task_result = job.result
      task_obj = {'task_id': job_id, \
                  'task_status': task_status, \
                  'task_result': task_result}
      data['jobs'].append(task_obj)
    return json.dumps({'response': data})
  else:
    return jsonify({'status': 'error'})

#https://stackoverflow.com/questions/15182696/multiple-parameters-in-in-flask-approute

@api.route('/task/<queue>/<task_id>', methods=['GET','POST'])
def get_status(queue = None, task_id = None):
  return get_task_status(queue, task_id)


@api.route('/queue_count', methods=['GET', 'POST'])#, 'OPTIONS'])
def queue_count():
  queue_out = {}
  csv_out = str(int(time.time()))
  csv_out += ','
  with Connection(redis.from_url(current_app.config['REDIS_URL'])):
    q = Queue('default')
    f_registry = FinishedJobRegistry('default')
    csv_out += str(len(q))
    csv_out += ','
    csv_out += str(len(f_registry.get_job_ids()))
  csv_out += '\n'
  return csv_out

@api.route('/getmetas', methods=['GET', 'POST'])
def getmetas():
  with Connection(redis.from_url(current_app.config['REDIS_URL'])):
    q = Queue('default')
    registry = StartedJobRegistry('default')
    f_registry = FinishedJobRegistry('default')

    all_task_ids = getalltasksID()
    # if request.method == 'GET':
    response_text = all_task_ids.get_data(as_text=True)

    response_json = all_task_ids.get_json()
    # data = json.load(response_json)
    running_tasks_ids = response_json["running"]["running_tasks_ids"]
    finished_tasks_ids = response_json["finished"]["finished_tasks_ids"]
    queued_tasks_ids = response_json["queued"]["queued_tasks_ids"]

    data = {}

    data['running_tasks'] = []
    for task_id in running_tasks_ids:
      d = {}
      job = q.fetch_job(task_id)
      job.refresh()
      job.meta['result'] = 'null'
      d[task_id] = job.meta
      data['running_tasks'].append(d)

    data['queued_tasks'] = []
    for task_id in queued_tasks_ids:
      d = {}
      job = q.fetch_job(task_id)
      job.refresh()
      job.meta['result'] = 'null'
      d[task_id] = job.meta
      data['queued_tasks'].append(d)

    data['finished_tasks'] = []
    for task_id in finished_tasks_ids:
      d = {}
      job = q.fetch_job(task_id)
      job.refresh()
      job.meta['result'] = job.result
      d[task_id] = job.meta
      data['finished_tasks'].append(d)

  with Connection(redis.from_url(current_app.config['REDIS_URL'])):
    q = Queue('aggregator')

    agg_fin_task_ids = get_all_finished_tasks_from('aggregator')
    temp = agg_fin_task_ids.get_json()
    agg_fin_tasks_ids = temp["finished"]["finished_tasks_ids"]

    agg_que_task_ids = get_all_queued_tasks_from('aggregator')
    temp = agg_que_task_ids.get_json()
    agg_que_tasks_ids = temp["queued"]["queued_tasks_ids"]

    agg_run_task_ids = get_all_running_tasks_from('aggregator')
    temp = agg_run_task_ids.get_json()
    agg_run_tasks_ids = temp["running"]["running_tasks_ids"]

    data['agg_finished_tasks'] = []
    for task_id in agg_fin_tasks_ids:
      d = {}
      job = q.fetch_job(task_id)
      if job is not None:
        job.refresh()
        job.meta['result'] = job.result
        d[task_id] = job.meta
        data['agg_finished_tasks'].append(d)

    data['agg_queued_tasks'] = []
    for task_id in agg_que_tasks_ids:
      d = {}
      job = q.fetch_job(task_id)
      if job is not None:
        job.refresh()
        job.meta['result'] = job.result
        d[task_id] = job.meta
        data['agg_queued_tasks'].append(d)

    data['agg_running_tasks'] = []
    for task_id in agg_run_tasks_ids:
      d = {}
      job = q.fetch_job(task_id)
      if job is not None:
        job.refresh()
        job.meta['result'] = job.result
        d[task_id] = job.meta
        data['agg_running_tasks'].append(d)

  return jsonify(data)

@api.route('/get_exec_times', methods=['GET', 'POST'])
def get_exec_times():
  data = {}
  # Get the execution timing info
  data['exec_time_logs'] = get_all_exec_time_logs()
  return jsonify(data)

@api.route('/set_redis', methods=['GET','POST'])
def set_redis():
  try:
    r = redis.StrictRedis(host="redis", port=6379, password="", decode_responses=True)
    r.set("msg:hello", "Hello Redis!!!")
    print(r.get("msg:hello"))
    return "Redis inserted"
  except Exception as e:
    print(e)

@api.route('/check_redis/<key>', methods=['GET','POST'])
def check_redis(key):
  r = redis.StrictRedis(host="redis", port=6379, password="", decode_responses=True)
  status = r.get(key)
  node_count = r.get(key + NODE_COUNT)
  done_node_count = r.get(key + DONE_NODE_COUNT)

  d = {'id': key, 'status': status, 'node_count': node_count, 'done_node_count': done_node_count}
  if status is not None:
    return jsonify(d)
  else:
    return "Empty"

@api.route('/get_redis', methods=['GET','POST'])
def get_redis():
  r = redis.StrictRedis(host="redis", port=6379, password="", decode_responses=True)
  output = r.get("msg:hello")
  if output is not None:
    return output
  else:
    return "Empty"

@api.route('/flush_redis', methods=['GET','POST'])
def flush_redis():
  with Connection(redis.from_url(current_app.config['REDIS_URL'])):
    queues = ['default', 'aggregator']

    for queue in queues:
      q = Queue(queue)
      f_registry = FinishedJobRegistry(queue)
      finished_job_ids = f_registry.get_job_ids()

      for f_job_id in finished_job_ids:
        j = q.fetch_job(f_job_id)
        j.cleanup(0)

  return "Flushed"
'''
  try:
    r = redis.StrictRedis(host="redis", port=6379, password="", decode_responses=True)
    r.set("msg:hello", "Hello Redis!!!")
    output = r.flushall()
    return "Flushed"
  except Exception as e:
    print(e)
    return e
'''

def fix_labels(label):
  #Labels
  #For feature extraction i think
  # %%time
  reshape_label = label.reshape(len(label)//window_size, window_size)

  correct_label = []

  for i in range(reshape_label.shape[0]):
      rows = reshape_label[i, :]
      unique, counts = np.unique(rows, return_counts=True)
      out = np.asarray((unique, counts)).T
      if out[0][1] != float(window_size):
          max_ind = np.argmax(np.max(out, axis=1))
          correct_label.append(out[max_ind, 0])
      elif out[0][1] == float(window_size):
          correct_label.append(out[0][0])

  y = np.array(correct_label)
  print(y.shape)
  return y

TARGET_NAMES = ["still", "walk",  "run",  "bike",  "car",  "bus",  "train",  "subway"]
NUM_CLASSES = len(TARGET_NAMES)
window_size = 100

def get_current_time():
  HERE = tz.gettz('Asia/Tokyo')
  UTC = tz.gettz('UTC')

  ts = datetime.datetime.utcnow().replace(tzinfo=UTC).astimezone(HERE)
  # local_time = ts.strftime('%Y-%m-%d %H:%M:%S.%f %Z%z')
  local_time = ts.strftime('%Y-%m-%d %H:%M:%S.%f %Z')[:-3]
  return local_time

def get_redis_server_time():
  # Start a redis connection
  r = redis.StrictRedis(host="redis", port=6379, password="", decode_responses=True)
  sec, microsec = r.time()
  return ((sec * 1000000) + microsec)

def initialize_query(total, count_suffix=NODE_COUNT, done_count_suffix=DONE_NODE_COUNT):
  r = redis.StrictRedis(host="redis", port=6379, password="", decode_responses=True)

  unique_id = funcs.generate_unique_ID()
  funcs.setRedisKV(r, unique_id, 'ongoing')
  funcs.setRedisKV(r, unique_id + count_suffix, total)
  funcs.setRedisKV(r, unique_id + done_count_suffix, 0)

  return unique_id

def add_exec_time_info(unique_id, operation, time_start, time_end):
  try:
    r = redis.StrictRedis(host="redis", port=6379, password="", decode_responses=True)

    # Add the unique_id to the execution time info list if it does not yet exist
    r.sadd(EXEC_TIME_INFO, unique_id)

    # Push an operation to the execution time log for this unique_id
    log_obj = {
      'operation'   : operation,
      'start_time'  : str(time_start),
      'end_time'    : str(time_end),
      'duration'    : str(float(time_end - time_start) / 1000000.0),
    }
    r.lpush("{}_{}".format(EXEC_TIME_INFO, unique_id), json.dumps(log_obj))

  except Exception as e:
    return False

  return True

def get_exec_time_log_ids():
  try:
    r = redis.StrictRedis(host="redis", port=6379, password="", decode_responses=True)
    return r.smembers(EXEC_TIME_INFO)

  except Exception as e:
    pass

  return None

def get_exec_time_log(unique_id):
  try:
    r = redis.StrictRedis(host="redis", port=6379, password="", decode_responses=True)
    list_id = "{}_{}".format(EXEC_TIME_INFO, unique_id)
    #return r.get("{}_{}".format(EVENT_LOGS, unique_id))
    item_count = r.llen(list_id)

    logs = []
    for i in range(0, item_count):
      logs.append(json.loads(r.lindex(list_id, i)))

    return logs

  except Exception as e:
    pass

  return []

def get_all_exec_time_logs():
  exec_time_log_ids = get_exec_time_log_ids()

  logs = {}
  for uid in exec_time_log_ids:
    logs[uid] = get_exec_time_log(uid)

  return logs

def enqueue_npy_files(unique_ID, model_type, chunk_list, mp_q):
  label_list = []
  data_list = []
  np_data_arrays = []
  with Connection(redis.from_url(current_app.config['REDIS_URL'])):
    q = Queue('default')
    print("Handling chunks: ", chunk_list)
    for chunk in chunk_list:
      filename = 'labels_' + str(chunk) + '.npy'
      path = os.path.join(current_app.instance_path, 'htmlfi/Chunks', filename)
      label = np.load(path)
      label_list.append(label)

      for i, name in enumerate(feat_name_list):
        raw_filename = name + '_' + str(chunk) + '.npy'
        raw_path = os.path.join(current_app.instance_path, 'htmlfi/Chunks', raw_filename)
        np_temp = np.load(raw_path)
        if len(np_data_arrays) == len(feat_name_list):
          np_data_arrays[i].extend([np_temp])
        else:
          np_data_arrays.append([np_temp])

    label_all = np.concatenate(label_list)
    y = fix_labels(label_all)
    y_str = y.tostring()

    for np_data_array in np_data_arrays:
      np_all = np.concatenate(np_data_array)
      all_str = np_all.tostring()
      data_list.append(all_str)

    task = q.enqueue('NUTS_Tasks.feat_Extract_And_Classify', data_list, y_str, model_type, unique_ID)
    response_object = {
        'status': 'success',
        'unique_ID': 'NUTS FEAT EXTRACT',
        'data_list_len': len(data_list[0]),
        'y_str_len': len(y_str),
        'model_type': model_type,
        'chunk_list': chunk_list,
        'data': {
          'task_id': task.get_id()
      }
    }
    mp_q.put(response_object)

#TODO: Fix for moren odes above 3
@api.route('/nuts_classify', methods=['GET', 'POST'])#, 'OPTIONS'])
def nuts_classify():
  with Connection(redis.from_url(current_app.config['REDIS_URL'])):
    q = Queue('default')
    #form = TextForm(meta={'csrf_context': request.remote_addr})
    form = TextForm(meta={'csrf_context': 'secret_key'})
    if form.validate_on_submit():
      tic = time.clock()
      node_count = form.node_count.data
      number_of_chunks = form.chunk_count.data
      model_type = form.model_type.data

      if node_count > number_of_chunks:
        #Maybe i should just divide the chunks, no! haha 
        return jsonify({'status':'node_count is greater than chunk_count'}), 616

      unique_ID = initialize_query(node_count)
      total_chunks = 200 #hard coded because i only saved 15 chunks in the server
      #Now need to make everything into lists
      chunks = []
      while len(chunks) != number_of_chunks:
        single_chunk = np.random.randint(0, total_chunks)
        if single_chunk in chunks:
          continue
        else:
          chunks.append(single_chunk)

      div, mod = divmod(number_of_chunks, node_count)

      index = 0
      chunk_lists = []
      node_data_list = []
      node_label_list = []

      for i in range(node_count):
        slice = chunks[index: index + div]
        index += div
        chunk_lists.append(slice)

      for i in range(mod):
        slice = chunks[index: index + div]
        chunk_lists[i].extend(slice)
        index += div

      #For debugging, need 202 return no.
      # return jsonify(chunk_lists[0]), 202

      json_response = {}
      json_response['tasks'] = []
      json_response['query_ID'] = unique_ID
      #json_response['query_received'] = int(time.time())
      json_response['query_received'] = get_current_time()

      out_q = multiprocessing.Queue()
      procs = []
      for chunk_list in chunk_lists:
        p = multiprocessing.Process(target=enqueue_npy_files, args=(unique_ID, model_type, chunk_list, out_q))
        procs.append(p)
        p.start()

      for chunk_list in chunk_lists:
        json_response['tasks'].append(out_q.get())

      for p in procs:
        p.join()

      toc = time.clock()
      json_response['progress'] = toc - tic
      return jsonify(json_response), 202
    elif form.csrf_token.errors:
      return jsonify({'status':'csrf_token_errors'})
    else:
      return jsonify({'status':'error'})

@api.route('/nuts2_classify', methods=['GET', 'POST'])#, 'OPTIONS'])
def nuts2_classify():
  with Connection(redis.from_url(current_app.config['REDIS_URL'])):
    q = Queue('default')
    form = Nuts2Form()
    if form.validate_on_submit():
      req = request.json
      tic = time.clock()
      node_count = req['node_count']
      number_of_chunks = req['chunk_count']
      model_type = req['model_type']

      if node_count > number_of_chunks:
        #Maybe i should just divide the chunks, no! haha 
        return jsonify({'status':'node_count is greater than chunk_count'}), 616

      unique_ID = initialize_query(node_count)
      total_chunks = 200 #hard coded because i only saved 15 chunks in the server
      #Now need to make everything into lists
      chunks = []
      while len(chunks) != number_of_chunks:
        single_chunk = np.random.randint(0, total_chunks)
        if single_chunk in chunks:
          continue
        else:
          chunks.append(single_chunk)

      div, mod = divmod(number_of_chunks, node_count)

      index = 0
      chunk_lists = []
      node_data_list = []
      node_label_list = []

      for i in range(node_count):
        slice = chunks[index: index + div]
        index += div
        chunk_lists.append(slice)

      for i in range(mod):
        slice = chunks[index: index + div]
        chunk_lists[i].extend(slice)
        index += div

      #For debugging, need 202 return no.
      # return jsonify(chunk_lists[0]), 202

      json_response = {}
      json_response['tasks'] = []
      json_response['query_ID'] = unique_ID
      #json_response['query_received'] = int(time.time())
      json_response['query_received'] = get_current_time()

      out_q = multiprocessing.Queue()
      procs = []
      for chunk_list in chunk_lists:
        p = multiprocessing.Process(target=enqueue_npy_files, args=(unique_ID, model_type, chunk_list, out_q))
        procs.append(p)
        p.start()

      for chunk_list in chunk_lists:
        json_response['tasks'].append(out_q.get())

      for p in procs:
        p.join()

      toc = time.clock()
      json_response['progress'] = toc - tic
      return jsonify(json_response), 202
    else:
      return jsonify({'status':'error'})

def convertIntToLocalTime(input):
    # METHOD 1: Hardcode zones:
    # from_zone = tz.gettz('UTC')
    # to_zone = tz.gettz('America/New_York')

    # METHOD 2: Auto-detect zones:
    from_zone = tz.tzutc()
    to_zone = tz.tzlocal()

    # 1537323289425,1533650065704
    # 1540263839999000064
    ts = int(input)
    ts /= 1000

    utc = datetime.datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
    local = datetime.datetime.strptime(utc, '%Y-%m-%d %H:%M:%S')#.replace(tzinfo=from_zone).astimezone(to_zone)
    return local.strftime('%Y-%m-%d %H:%M:%S')

@api.route('/dt_get_readable', methods=['GET', 'POST'])#, 'OPTIONS'])
def dt_get_readable():
  req = request.get_json(force=True)
  influx_ip = req['influx_ip']

  if influx_ip == '163.221.68.206':
    headers: { 'Accept': 'application/csv' }
    payload = {
      "db": 'bl01_db',
      "pretty": True,
      "epoch": 'ms',
      "q": 'SELECT last(accel_y) from "bl01_db"."autogen"."meas_1"'
    }
    r = requests.get('http://' + influx_ip +':8086/query', params=payload)
    last = json.loads(r.text)
    last_time_int = last["results"][0]["series"][0]["values"][0][0]

    payload = {
      "db": 'bl01_db',
      "pretty": True,
      "epoch": 'ms',
      "q": 'SELECT first(accel_y) from "bl01_db"."autogen"."meas_1"'
    }
    r = requests.get('http://163.221.68.206:8086/query', params=payload)
    first = json.loads(r.text)
    first_time_int = first["results"][0]["series"][0]["values"][0][0]
    return str(convertIntToLocalTime(first_time_int)) + ';' + str(convertIntToLocalTime(last_time_int))
    # return str(first_time_int) + ',' + str(last_time_int)
  elif influx_ip == '163.221.68.191':
    DB = 'IFoT-GW2'
    query = "SELECT first(accel_y) from \"autogen\".\"" + DB + "-Meas\""
    payload = {
    "db": DB,
    "pretty": True,
    "epoch": 'ms',
    "q": query
    }
    #curl -G 'http://163.221.68.191:8086/query?db=IFoT-GW1' --data-urlencode 'q=SELECT last(accel_y) from "autogen"."IFoT-GW1-Meas"'
    r = requests.get('http://163.221.68.191:8086/query?', params=payload)
    #FOR SOPICHA
    print(r.text)
    first = json.loads(r.text)
    first_t = first["results"][0]["series"][0]["values"][0][0]

    #EARLIEST-LATEST date getter
    query = "SELECT last(accel_y) from \"autogen\".\"" + DB + "-Meas\""
    payload = {
    "db": DB,
    "pretty": True,
    "epoch": 'ms',
    "q": query
    }
    #curl -G 'http://163.221.68.191:8086/query?db=IFoT-GW1' --data-urlencode 'q=SELECT last(accel_y) from "autogen"."IFoT-GW1-Meas"'
    r = requests.get('http://163.221.68.191:8086/query?', params=payload)
    last = json.loads(r.text)
    last_t = last["results"][0]["series"][0]["values"][0][0]
    return str(convertIntToLocalTime(first_t)) + ';' + str(convertIntToLocalTime(last_t))
    # return str(first_t) + ',' + str(last_t)

@api.route('/dt_get', methods=['GET', 'POST'])#, 'OPTIONS'])
def dt_get():
  req = request.get_json(force=True)
  influx_ip = req['influx_ip']

  if influx_ip == '163.221.68.206':
    headers: { 'Accept': 'application/csv' }
    payload = {
      "db": 'bl01_db',
      "pretty": True,
      "epoch": 'ms',
      "q": 'SELECT last(accel_y) from "bl01_db"."autogen"."meas_1"'
    }
    r = requests.get('http://' + influx_ip +':8086/query', params=payload)
    last = json.loads(r.text)
    last_time_int = last["results"][0]["series"][0]["values"][0][0]

    payload = {
      "db": 'bl01_db',
      "pretty": True,
      "epoch": 'ms',
      "q": 'SELECT first(accel_y) from "bl01_db"."autogen"."meas_1"'
    }
    r = requests.get('http://163.221.68.206:8086/query', params=payload)
    first = json.loads(r.text)
    first_time_int = first["results"][0]["series"][0]["values"][0][0]
    # return str(convertIntToLocalTime(first_time_int)) + ',' + str(convertIntToLocalTime(last_time_int))
    return str(first_time_int) + ';' + str(last_time_int)
  elif influx_ip == '163.221.68.191':
    DB = 'IFoT-GW2'
    query = "SELECT first(accel_y) from \"autogen\".\"" + DB + "-Meas\""
    payload = {
    "db": DB,
    "pretty": True,
    "epoch": 'ms',
    "q": query
    }
    #curl -G 'http://163.221.68.191:8086/query?db=IFoT-GW1' --data-urlencode 'q=SELECT last(accel_y) from "autogen"."IFoT-GW1-Meas"'
    r = requests.get('http://163.221.68.191:8086/query?', params=payload)
    #FOR SOPICHA
    print(r.text)
    first = json.loads(r.text)
    first_t = first["results"][0]["series"][0]["values"][0][0]

    #EARLIEST-LATEST date getter
    query = "SELECT last(accel_y) from \"autogen\".\"" + DB + "-Meas\""
    payload = {
    "db": DB,
    "pretty": True,
    "epoch": 'ms',
    "q": query
    }
    #curl -G 'http://163.221.68.191:8086/query?db=IFoT-GW1' --data-urlencode 'q=SELECT last(accel_y) from "autogen"."IFoT-GW1-Meas"'
    r = requests.get('http://163.221.68.191:8086/query?', params=payload)
    last = json.loads(r.text)
    last_t = last["results"][0]["series"][0]["values"][0][0]
    # return str(convertIntToLocalTime(first_t)) + ',' + str(convertIntToLocalTime(last_t))
    return str(first_t) + ';' + str(last_t)

def convert_utc_to_epoch(timestamp_string):
    '''Use this function to convert utc to epoch'''
    timestamp = datetime.datetime.strptime(timestamp_string, '%Y-%m-%d %H:%M:%S')
    epoch = int(calendar.timegm(timestamp.utctimetuple()))
    print(epoch)
    return int(epoch) * 1000

def enqueue_heatmap_queries(start_time, end_time, feature, mp_q):
  with Connection(redis.from_url(current_app.config['REDIS_URL'])):
    q = Queue('default')


    mp_q.put(response_object)

#TODO: Breakdown the time/duration and then send the unix times to the various nodes.
@api.route('/heatmap_trigger', methods=['POST'])#, 'OPTIONS'])
def heatmap_trigger():
  req = request.get_json(force=True)
  influx_ip = req['influx_ip']
  start_time = req['start_time']
  end_time = req['end_time']
  feature = req['feature']
  
  with Connection(redis.from_url(current_app.config['REDIS_URL'])):
    q = Queue('default')
    json_response = {}
    json_response['query_ID'] = 'unique_ID'
    json_response['query_received'] = get_current_time()

    task = q.enqueue('HEATMAP_Tasks.readSVG', influx_ip, start_time, end_time, feature)
    params = str(start_time) + " to " + str(end_time) + " of feature: " + feature
    response_object = {
      'status': 'success',
      'unique_ID': 'HEATMAP READ SVG',
      'params': params,
      'data': {
        'task_id': task.get_id()
      }
    }
    json_response['response_object'] = response_object

    return jsonify(json_response), 202

  # return str(start_time) + ',' + str(end_time) + ',' + feature

def query_influx_db(start, end, fields="*",
                                influx_db='IFoT-GW2',
                                influx_ret_policy='autogen',
                                influx_meas='IFoT-GW2-Meas',
                                host='163.221.68.191',
                                port='8086'):

    source = '"{}"."{}"."{}"'.format(influx_db, influx_ret_policy, influx_meas)
    where  = 'WHERE time >= {} AND time <= {}'.format(start, end)
    query = "SELECT * from {} {}".format(fields, source, where)

    payload = {
        "db": DB,
        "pretty": True,
        "epoch": 'ms',
        "q": query
    }

    influx_url = "http://{}:{}/query".format(host, port)
    return requests.get(influx_url, params=payload)

@api.route('/get_raw_labels', methods=['GET'])#, 'OPTIONS'])
def get_raw_labels():
  resp = ""
  try:
    f = open("static/raw_labels.csv", "r")
    resp = {"status" : "success", "contents" : f.read()}

  except Exception as e:
    resp = {"status" : "failed", "error" : str(e)}

  return jsonify(resp), 200

@api.route('/get_training_labels', methods=['GET'])#, 'OPTIONS'])
def get_training_labels():
  labels = []

  try:
    # See if we have any files cached
    if os.path.isfile("static/raw_labels-cached.json"):

      cached_last_mod = os.stat("static/raw_labels-cached.json").st_mtime
      ref_last_mod =  os.stat("static/raw_labels.csv").st_mtime

      # If cached file is newer than the reference file, we can
      #  still reuse it
      if cached_last_mod > ref_last_mod:
        resp = ""
        with open("static/raw_labels-cached.json", "r") as f:
          resp = f.read()

        return resp, 200

    fmt_date = "%Y-%m-%d %H:%M.%S"
    date_convert = lambda d: datetime.datetime.strptime(d, fmt_date) - \
                             datetime.timedelta(hours=9)

    with open("static/raw_labels.csv", newline='') as csvf:
      reader =  csv.DictReader(csvf)
      activity_list = []
      for row in reader:
        if not row['Activity'] in activity_list:
          activity_list.append(row['Activity'])

        proper_row = {
          "Activity" : row['Activity'],
          "ActivityId" : activity_list.index(row["Activity"]),
          "End" : date_convert(row['End']).timestamp(),
          "Start" : date_convert(row['Start']).timestamp(),
        }
        labels.append(proper_row)

    # Cache the file
    with open("static/raw_labels-cached.json", "w") as f:
      f.write(json.dumps(labels))

  except Exception as e:
    labels.append({"status" : "failed", "error" : str(e)})

  return json.dumps(labels), 200

def enqueue_classify_task(queue, unique_id, seq_id, model, sensor_list, param_list,
                          columns, values):

  with Connection(redis.from_url(current_app.config['REDIS_URL'])):
    q = Queue('default')

    task = q.enqueue('ActivityRecog_Tasks.classify', unique_id, seq_id,
                        model, sensor_list, param_list,
                        columns, values)

  queue.put(task.get_id())
  return

#TODO: Breakdown the time/duration and then send the unix times to the various nodes.
@api.route('/classify_activity', methods=['POST'])#, 'OPTIONS'])
def classify_activity():
  collect_start_time = get_redis_server_time()

  tic = time.perf_counter()
  req = request.get_json(force=True)
  influx_ip   = req['influx_ip']
  model = req['model']
  sensor_list = req['sensor_list']  # List(string), sensor addresses to use for training
  param_list = req['param_list']    # List(string), params to use
  start_time  = req['start_time']
  end_time    = req['end_time']
  split_count = int(req['split_count'])
  # node_count  = int(req['node_count'])
  # feature     = req['feature']

  # Obtain a unique ID
  unique_id = initialize_query(split_count, count_suffix=TASK_COUNT, done_count_suffix=DONE_TASK_COUNT)

  # Retrieve the data to be classified from Influx DB
  if influx_ip == "" or influx_ip == "DEFAULT":
    influx_ip = 'IFoT-GW2'

  resp = query_influx_db(start_time, end_time, influx_db=influx_ip)

  columns = np.asarray( json.loads(resp.text)['results'][0]['series'][0]['columns'] )
  values = np.asarray( json.loads(resp.text)['results'][0]['series'][0]['values'] )

  # Based on the number of columns we received assess how we would split
  split_rows_count = int(len(values) / split_count) + 1

  task_ids = []
  json_response = {}
  json_response['query_ID'] = unique_id
  json_response['query_received'] = get_current_time()

  start_idx = 0
  end_idx   = split_rows_count
  seq_id    = 0

  processes = []
  mpq = multiprocessing.Queue()
  while start_idx < len(values):
    p = multiprocessing.Process(target=enqueue_classify_task,
                                args=(mpq, unique_id, seq_id, model, sensor_list, param_list,
                                      columns, values[start_idx:end_idx]))

    processes.append(p)
    p.start()

    # Update the sequence id for the next
    seq_id += 1

    # Update our indices
    start_idx = end_idx + 1
    if end_idx + split_rows_count > len(values):
      end_idx = len(values)
      continue

    end_idx += split_rows_count

  for p in processes:
    task = mpq.get()
    task_ids.append(task)

  for p in processes:
    p.join()

  toc = time.perf_counter()
  response_object = {
    'status': 'success',
    'unique_ID': unique_id,
    'params': {
      'start_time'  : start_time,
      'end_time'    : end_time,
      'split_count' : split_count
    },
    'data': {
      'task_id': task_ids
    },
    "benchmarks" : {
      "exec_time" : str(toc - tic),
    }
  }

  # return str(start_time) + ',' + str(end_time) + ',' + feature
  json_response['response_object'] = response_object
  api_resp = jsonify(json_response)

  # Log execution time info to redis
  add_exec_time_info(unique_id, "collection", collect_start_time, get_redis_server_time())

  return api_resp, 202

@api.route('/train_activities', methods=['POST'])#, 'OPTIONS'])
def train_activities():
  collect_start_time = get_redis_server_time()

  tic = time.perf_counter()
  req = request.get_json(force=True)
  influx_ip   = req['influx_ip']
  start_time  = req['start_time']   # Long Integer, training data start timestamp
  end_time    = req['end_time']     # Long Integer, training data end timestamp
  sensor_list = req['sensor_list']  # List(string), sensor addresses to use for training
  strategy    = req['strategy']     # String,       strategy for distributed training: 'one_per_sensor' (default), 'one_for_all', 'all'
  split_count = req['split_count']  # Integer,      number of training tasks to create; ignored if 'one_per_sensor' is used
  model       = req['model']        # String,       machine learning model to train

  # If we are using the 'one_per_sensor' strategy, then we have to
  #   override the split_count to generate one training task for
  #   each sensor to be used
  if strategy == 'one_per_sensor':
    split_count = len(sensor_list)

  # Obtain a unique ID
  unique_id = initialize_query(split_count, count_suffix=TASK_COUNT, done_count_suffix=DONE_TASK_COUNT)

  # Retrieve the data to be classified from Influx DB
  if influx_ip == "" or influx_ip == "DEFAULT":
    influx_ip = 'IFoT-GW2'

  resp = query_influx_db(start_time, end_time, influx_db=influx_ip)
  # Split into columns and values
  columns = np.asarray( json.loads(resp.text)['results'][0]['series'][0]['columns'] )
  values = np.asarray( json.loads(resp.text)['results'][0]['series'][0]['values'] )

  # Prepare the JSON response in advance
  json_response = {}
  json_response['query_ID'] = unique_id
  json_response['query_received'] = get_current_time()

  # Distribute data for training
  task_ids = []
  seq_id = 0
  param_list = [ 'humidity', 'light', 'noise', 'rssi', 'temperature' ]
  for i in range(0, split_count):
    # By default, indicate that all sensor addresses are to be used
    use_sensors = sensor_list

    # Except when using the 'one_per_sensor' strategy
    if strategy == 'one_per_sensor':
      use_sensors = [ sensor_list[i] ]

    with Connection(redis.from_url(current_app.config['REDIS_URL'])):
      q = Queue('default')
      task = q.enqueue( 'ActivityRecog_Tasks.train',
                        unique_id, seq_id, model, use_sensors, param_list,
                        columns, values,
                        "http://163.221.68.242:5001/api/get_training_labels",
                        "http://163.221.68.242:5001/api/upload_classifier" )
      task_ids.append( task.get_id() )
      seq_id += 1

  toc = time.perf_counter()

  # Finalize the response
  response_object = {
    'status': 'success',
    'unique_ID': unique_id,
    'params': {
      'start_time'  : start_time,
      'end_time'    : end_time,
      'split_count' : split_count
    },
    'data': {
      'task_id': task_ids
    },
    "benchmarks" : {
      "exec_time" : str(toc - tic),
    }
  }

  # return str(start_time) + ',' + str(end_time) + ',' + feature
  json_response['response_object'] = response_object
  api_resp = jsonify(json_response)

  # Log execution time info to redis
  add_exec_time_info(unique_id, "collection", collect_start_time, get_redis_server_time())

  return api_resp, 202

@api.route('/uploads/<filename>')
def uploaded_file(filename):
  return send_from_directory("uploads", filename)

@api.route('/upload_classifier', methods=['POST'])#, 'OPTIONS'])
def upload_classifier():
  if 'file' not in request.files:
    return "File not found", 400

  file = request.files['file']
  if file.filename == '':
    return "No filename", 400

  if file:
    filename = secure_filename(file.filename)
    file.save(os.path.join("uploads", filename))

    # TODO Move to a separate thread?
    # Notify other S-Workers of the new classifier file
    last_changed = os.stat("uploads/{}".format(filename)).st_mtime
    unique_id = '{}'.format( int(datetime.datetime.now().timestamp()) )
    download_url = "http://163.221.68.242:5001{}".format( url_for("api.uploaded_file", filename=filename) )
    task_ids = []
    for seq_id in range(0, 16):
      with Connection(redis.from_url(current_app.config['REDIS_URL'])):
        q = Queue('default')

        task = q.enqueue('ActivityRecog_Tasks.download_classifier',
                            unique_id, seq_id,
                            download_url,
                            last_changed )

        task_ids.append( task.get_id() )

    return "Success: {}".format(url_for("api.uploaded_file",
                                        filename=filename)), 200

  return "Failed", 404

def enqueue_average_speed_task(queue, unique_id, seq_id, columns, values):
  with Connection(redis.from_url(current_app.config['REDIS_URL'])):
    q = Queue('default')

    task = q.enqueue('VASMAP_Tasks.average', unique_id, seq_id, columns, values)

  queue.put(task.get_id())
  return


@api.route('/vas/get_average_speeds', methods=['GET'])
def get_average_speeds():
  collect_start_time = get_redis_server_time()

  tic = time.perf_counter()
  req = request.get_json(force=True)

  influx_ip   = req['influx_ip']
  rsu_list    = req['rsu_list']
  start_time  = req['start_time']       # Long Integer
  end_time    = req['end_time']         # Long Integer
  split_count = int(req['split_count']) # Integer

  # Obtain a unique ID
  unique_id = initialize_query(split_count, count_suffix=TASK_COUNT, done_count_suffix=DONE_TASK_COUNT)

  # Retrieve the data to be classified from Influx DB
  if influx_ip == "" or influx_ip == "DEFAULT":
    influx_ip = '163.221.68.206'

  resp = query_influx_db( start_time, end_time,
                          host=influx_ip,
                          port='8086',
                          influx_db='VASMAP',
                          influx_ret_policy='default_rp',
                          influx_meas='rsu_data' )

  # Split into columns and values
  columns = np.asarray( json.loads(resp.text)['results'][0]['series'][0]['columns'] )
  values = np.asarray( json.loads(resp.text)['results'][0]['series'][0]['values'] )

  # Based on the number of columns we received assess how we would split
  split_rows_count = int(len(values) / split_count) + 1

  task_ids = []
  json_response = {}
  json_response['query_ID'] = unique_id
  json_response['query_received'] = get_current_time()

  start_idx = 0
  end_idx   = split_rows_count
  seq_id    = 0

  processes = []
  mpq = multiprocessing.Queue()
  while start_idx < len(values):
    p = multiprocessing.Process(target=enqueue_classify_task,
                                args=(mpq, unique_id, seq_id, columns, values[start_idx:end_idx]))

    processes.append(p)
    p.start()

    # Update the sequence id for the next
    seq_id += 1

    # Update our indices
    start_idx = end_idx + 1
    if end_idx + split_rows_count > len(values):
      end_idx = len(values)
      continue

    end_idx += split_rows_count

  for p in processes:
    task = mpq.get()
    task_ids.append(task)

  for p in processes:
    p.join()

  toc = time.perf_counter()

  # Finalize the response
  response_object = {
    'status': 'success',
    'unique_ID': unique_id,
    'params': {
      'start_time'  : start_time,
      'end_time'    : end_time,
      'split_count' : split_count
    },
    'data': {
      'task_id': task_ids
    },
    "benchmarks" : {
      "exec_time" : str(toc - tic),
    }
  }

  # return str(start_time) + ',' + str(end_time) + ',' + feature
  json_response['response_object'] = response_object
  api_resp = jsonify(json_response)

  # Log execution time info to redis
  add_exec_time_info(unique_id, "collection", collect_start_time, get_redis_server_time())

  return api_resp, 202


