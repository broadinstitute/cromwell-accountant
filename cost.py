#!/usr/bin/env python

from datetime import datetime
import json
from math import ceil
import requests
import sys

PRICELIST = 'http://cloudpricingcalculator.appspot.com/static/data/pricelist.json'

def get_pricelist():
    response = requests.get(PRICELIST)
    return response.json()['gcp_price_list']

def get_machine_info(call):
  zone, machine_type = call['jes']['machineType'].split('/')
  region = zone[:-2]
  return region, machine_type, call['preemptible']

def get_machine_hour(pricelist, region, machine_type, preemptible = False):
  price_key = 'CP-COMPUTEENGINE-VMIMAGE-' + machine_type.upper()
  if preemptible:
    price_key += '-PREEMPTIBLE'
  return pricelist[price_key][region]

def get_disk_hour(call, pricelist):
  region, _, preemptible = get_machine_info(call)
  disks = call['runtimeAttributes']['disks'].split(',')
  for disk in disks:
    _, disk_size, disk_type = disk.strip().split()
    price_key = 'CP-COMPUTEENGINE-'
    if disk_type == 'HDD':
      price_key += 'STORAGE-PD-CAPACITY'
    elif disk_type == 'SSD':
      price_key += 'STORAGE-PD'
    elif disk_type == 'LOCAL':
      disk_size = '375'
      price_key += 'LOCAL-SSD'
      if preemptible:
        price_key += '-PREEMPTIBLE'
  return pricelist[price_key][region] * int(disk_size)

def get_datetime(dt):
  return datetime.strptime(dt, '%Y-%m-%dT%X.%fZ')

def get_hours(call):
  start_time = get_datetime(call['start'])
  end_time = get_datetime(call['end']) if 'end' in call else datetime.now()
  delta = end_time - start_time
  seconds = delta.days * 24 * 3600 + delta.seconds
  return max(seconds, 60) / 3600.0

def get_price(metadata, pricelist):
  price = 0
  for calls in metadata['calls'].values():
    for call in calls:
      if 'jes' in call:
        machine_hour = get_machine_hour(pricelist, *get_machine_info(call))
        disk_hour = get_disk_hour(call, pricelist)
        hours = get_hours(call)
        price += (machine_hour + disk_hour) * hours
  return ceil(price * 100) / 100.0

def main():
  metadata = json.loads(sys.stdin.read())
  pricelist = get_pricelist()
  price = get_price(metadata, pricelist)
  print('$%.2f' % price)

if __name__ == '__main__':
    main()
