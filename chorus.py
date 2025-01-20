#!/usr/bin/env python3
import os
import sys
from sys import stderr

if sys.version_info < (3, 9):
  print("Python 3.9 or greater is required.", file=stderr)
  sys.exit(1)

def get_filenames_from_chorus() -> list[str]:
  home_dir = os.path.expanduser("~")
  chorus_dir = os.path.join(home_dir, ".chorus")
  if not os.path.exists(chorus_dir):
    return []
  return [os.path.join(chorus_dir, f) for f in os.listdir(chorus_dir) if os.path.isfile(os.path.join(chorus_dir, f))]

from dataclasses import dataclass
from typing import Literal, TypeAlias

@dataclass
class Message:
    role: Literal["system", "user", "assistant"]
    content: str

PlanDict: TypeAlias = dict[str, str | int | float | list[Message]]

plan: PlanDict = {
  "samples": [],
  "messages": [],
  "model": "gpt-4o-mini",
  "temperature": 1.0,
  "workers": 16,
  "maxRetries": 3,
  "baseUrl": "https://api.openai.com/v1",
  "apiKey": os.getenv("OPENAI_API_KEY"),
  "skip": 0,
  "output": "csv",
  "requestsPerSecond": 128
}

argument_iterator = iter(sys.argv[1:])
filenames: list[str] = get_filenames_from_chorus()

while (derp := next(argument_iterator, None)) != None:
  if derp.startswith("--"):
    key = derp[2:]
    value = next(argument_iterator)
    if key == 'skip':
      value = int(value)
    elif key == 'temperature':
      value = float(value)
    elif key == 'workers':
      value = int(value)
    elif key == 'maxRetries':
      value = int(value)
    if key == 'sample':
      plan['samples'].append(value)
    else:
      plan[key] = value
  else:
    filenames.append(derp)

def read_file(filename: str) -> PlanDict:
  import json
  # a file is either a JSON dictionary, or a list of strings.
  # if it opens with a {, it's a JSON dictionary.
  with open(filename, "r") as f:
    content = f.read()
    if content.strip().startswith('{'):
      return json.loads(content)
    else:
      return {
        "samples": content.splitlines()
      }

def merge_plan(current: PlanDict, new: PlanDict) -> PlanDict:
  for key, value in new.items():
    if key == "samples":
      current["samples"].extend(value)
    else:
      current[key] = value
  return current

ordered_plans = [read_file(filename) for filename in filenames]

for p in ordered_plans:
  plan = merge_plan(plan, p)

assert len(plan['samples']) > 0, "No samples provided"
assert len(plan['samples']) > plan['skip'], "Skip is greater than the number of samples"
assert plan['workers'] > 0, "Workers must be greater than 0"
assert plan['temperature'] >= 0, "Temperature must be greater than or equal to 0"
assert plan['temperature'] <= 2, "Temperature must be less than or equal to 2"
assert 'model' in plan, "Model must be provided"
assert 'messages' in plan, "Messages must be provided"
assert len(plan['messages']) > 0, "Messages must be provided"
assert 'apiKey' in plan, "API key must be provided"
assert 'baseUrl' in plan, "Base URL must be provided"
assert plan['skip'] >= 0, "Skip must be greater than or equal to 0"
assert plan['maxRetries'] >= 0, "Max retries must be greater than or equal to 0"

import time

def touch_temporal_cursor(cursor: float, period: float) -> tuple[float, float]:
  now: float = time.time()
  if now > cursor:
    return (now + period, 0)
  pause = cursor - now
  cursor = cursor + period
  return (cursor, pause)

temporal_cursor: float = time.time()
period: float = 1.0 / float(plan['requestsPerSecond'])

def throttle():
  global temporal_cursor
  temporal_cursor, pause = touch_temporal_cursor(temporal_cursor, period)
  if pause > 0:
    time.sleep(pause)

def call(
    plan: PlanDict,
    sample: str,
    attempt: int = 0,
) -> tuple[str, str]:
  throttle()
  headers = {
    "Authorization": f"Bearer {plan['apiKey']}",
    "Content-Type": "application/json",
  }
  first_attempt = attempt == 0
  temperature = float(plan['temperature'])
  temperature = temperature if first_attempt else max(0.5, temperature)
  messages = plan['messages'] + [{
    "role": "user",
    "content": sample,
  }]
  data = {
    "model": plan['model'],
    "temperature": temperature,
    "messages": messages,
  }
  import json
  submission = json.dumps(data)
  result = None
  try:
    import http.client
    base_url = plan['baseUrl']
    protocol = "https" if base_url.startswith("https") else "http"
    hostname = base_url.split("/")[2]
    conn = http.client.HTTPSConnection(hostname) if protocol == "https" else http.client.HTTPConnection(hostname)
    reszta = base_url[len(hostname) + len(protocol) + 3:]
    conn.request("POST", reszta + "/chat/completions", submission, headers)
    response = conn.getresponse()
    if response.status == 200:
      data = response.read()
      conn.close()
      result = json.loads(data.decode('utf-8'))
    elif response.status == 429:
      import random
      sleep_milliseconds = random.uniform(100, 1000)
      print(f"Too many requests, sleeping for {sleep_milliseconds}ms", file=stderr)
      import time
      time.sleep(sleep_milliseconds / 1000)
      return call(plan, sample, attempt + 1)
    else:
      raise Exception(f"HTTP {response.status} {response.reason}")
  except Exception as e:
    if first_attempt:
      raise e
    else:
      return call(plan, sample, attempt - 1)
  content = result["choices"][0]["message"]["content"]
  return sample, content

samples = plan['samples'][plan['skip']:]

protocol: Literal["jsonl", "csv", "asorted"] = plan['output']

def write_result(sample: str, content: str):
  if protocol == "jsonl":
    import json
    print(json.dumps({"sample": sample, "content": content}))
  elif protocol == "csv":
    def escape_for_csv(s: str):
      needs_escaping = [",", "\n", "\r", '"']
      if any(c in s for c in needs_escaping):
        return f'"{s.replace("\"", "\"\"")}"'
      else:
        return s
    print(f"{escape_for_csv(sample)},{escape_for_csv(content)}")
  elif protocol == "asorted":
    print(content)

from concurrent.futures import ThreadPoolExecutor

worker_count = plan['workers']

if protocol == "csv":
  print("sample,content")

with ThreadPoolExecutor(max_workers=worker_count) as executor:
  futures = [executor.submit(call, plan, sample) for sample in samples]
  for future in futures:
    sample, content = future.result()
    write_result(sample, content)




