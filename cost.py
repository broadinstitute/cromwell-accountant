#!/usr/bin/env python
import argparse
from datetime import datetime, timezone
import dateutil.parser
import json
from math import ceil
import requests
import sys

import firecloud.api as fapi

PRICELIST = 'http://cloudpricingcalculator.appspot.com/static/data/pricelist.json'
MONTH_HOURS = 730

T4_ONDEMAND_PRICE = 0.35
T4_PREEMPTIBLE_PRICE = 0.11

V100_ONDEMAND_PRICE = 2.48
V100_PREEMPTIBLE_PRICE = 0.74

gpuPriceDict = {"nvidia-tesla-t4" : 0.35, "nvidia-tesla-v100" : 2.48}
gpuPriceDict_PREEMPTIBLE = {"nvidia-tesla-t4" : 0.11, "nvidia-tesla-v100" : 0.74}


def get_pricelist():
    response = requests.get(PRICELIST)
    return response.json()['gcp_price_list']

def get_machine_info(call):
  jes = call['jes']
  zone = jes['zone']
  region = zone[:-2]
  machine_type = jes['machineType']
  if machine_type.startswith(zone):
    machine_type = machine_type.split('/')[1]
  #print(call, region, machine_type)
  return region, machine_type, call['preemptible']

def get_price_key(key, preemptible):
  return key + ('-PREEMPTIBLE' if preemptible else '')

def get_machine_hour(pricelist, region, machine_type, preemptible = False):
  price = 0
  if machine_type.startswith('custom'):
    _, core, memory = machine_type.split('-')
    core_key = get_price_key('CP-COMPUTEENGINE-CUSTOM-VM-CORE', preemptible)
    price += pricelist[core_key][region] * int(core)
    memory_key = get_price_key('CP-COMPUTEENGINE-CUSTOM-VM-RAM', preemptible)
    price += pricelist[memory_key][region] * ceil(int(memory) * 0.001)
  else:
    price_key = get_price_key(
      'CP-COMPUTEENGINE-VMIMAGE-' + machine_type.upper(), preemptible
    )
    price += pricelist[price_key][region] * memory * 0.001
  return price

def get_disk_hour(call, pricelist):
  region, _, preemptible = get_machine_info(call)
  disks = call['runtimeAttributes']['disks'].split(',')
  for disk in disks:
    _, disk_size, disk_type = disk.strip().split()
    price_key = 'CP-COMPUTEENGINE-'
    if disk_type == 'HDD':
      price_key += 'STORAGE-PD-CAPACITY'
    elif disk_type == 'SSD':
      price_key += 'STORAGE-PD-SSD'
    elif disk_type == 'LOCAL':
      disk_size = '375'
      price_key += 'LOCAL-SSD'
      if preemptible:
        price_key += '-PREEMPTIBLE'
  return pricelist[price_key][region] * int(disk_size) / MONTH_HOURS

def get_datetime(dt):
  return dateutil.parser.parse(dt)

def get_hours(call):
  start_time = get_datetime(call['start'])
  if 'end' in call:
      end_time = get_datetime(call['end'])
  else:
      end_time = datetime.now(timezone.utc)
  delta = end_time - start_time
  seconds = delta.days * 24 * 3600 + delta.seconds
  return max(seconds, 60) / 3600.0

def getGPUPriceHour(call):
    if "runtimeAttributes" not in call:
        return 0.0
    attributes = call["runtimeAttributes"]
    if "gpuType" in attributes and "gpuCount" in attributes:
        count = int(attributes["gpuCount"])
        gpu_type = str(attributes["gpuType"])
        gpu_price = count * (gpuPriceDict_PREEMPTIBLE[gpu_type] if call["preemptible"] else gpuPriceDict[gpu_type])
        return gpu_price
        
    return 0.0

def get_price(metadata, pricelist, price=0):
  for calls in metadata['calls'].values():
    for call in calls:
      #print(call["runtimeAttributes"])
      if 'jes' in call and 'zone' in call['jes'] and 'machineType' in call['jes']:
        gpu_per_hour = getGPUPriceHour(call) 
        machine_hour = get_machine_hour(pricelist, *get_machine_info(call))
        disk_hour = get_disk_hour(call, pricelist)
        hours = get_hours(call)
        price += (machine_hour + disk_hour + gpu_per_hour) * hours
      if "subWorkflowMetadata" in call:
        price += get_price(call["subWorkflowMetadata"], pricelist, price)
  return ceil(price * 100) / 100.0

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-N", "--namespace", dest="namespace", help="The Terra namespace containing the workspace (precedes the workspace at the top of the page).")
    parser.add_argument("-W", "--workspace", dest="workspace", help="The Terra workspace from which to retrieve job details.")
    parser.add_argument("-i", "--workflow-id", dest="workflow", help="The workflow ID, a UUID-style string, which can be found just below the job name.")
    parser.add_argument("-s", "--submission-id", dest="submission", help="The submission ID from the job manager page.")

    return parser.parse_args()

def main():
    
  args = parse_args()
  namespace = args.namespace
  workspace = args.workspace
  submission_id = args.submission
  workflow_id = args.workflow
  resp = fapi.get_workflow_metadata(namespace, workspace, submission_id, workflow_id)

  metadata = json.loads(resp.text)
  pricelist = get_pricelist()
  price = get_price(metadata, pricelist, price=0)
  print('$%.2f' % price)

if __name__ == '__main__':
    main()
