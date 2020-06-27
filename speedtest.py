import subprocess
import requests
import json
import os
import re
from datetime import datetime
from dateutil import tz
import calendar
import time
from threading import Event
import signal
from pathlib import Path

HOME = str(Path.home())
HOST_PATTERN = "^([a-zA-Z0-9\-\.]+):\d+$"

ELASTICSEARCH_URL = "http://localhost:9200/speedtest"
POST_HEADERS = {
    "User-Agent": "egg82/PyParser",
    "Accept": "application/json",
    "Connection": "close",
    "Accept-Language": "en-US,en;q=0.8",
    "Content-Type": "application/json"
}
FAILURES_FILE = "failures.txt"

SLEEP_TIME = 1200.0 # 20 mins

EXIT = Event()

def add_failure(data):
    if not os.path.exists(FAILURES_FILE):
        with open(FAILURES_FILE, "wt", encoding="utf8") as file:
            file.write(data + "\n")
    else:
        with open(FAILURES_FILE, "at", encoding="utf8") as file:
            file.write(data + "\n")

def submit_data(item_id, url, params):
    req = requests.post(url, headers=POST_HEADERS, json=params)
    if req.status_code < 200 or req.status_code >= 300:
        print("Got status code " + str(req.status_code) + " for " + item_id + ", skipping..")
        add_failure(json.dumps(params))
    else:
        print("Posted " + item_id + " to Elasticsearch!")

def main():
    while not EXIT.is_set():
        start_time = time.time()
        for i in range(0, 3):
            result = subprocess.run([HOME + "/.local/bin/speedtest-cli", "--json", "--secure"], stdout=subprocess.PIPE)
            output = result.stdout.decode("UTF-8")

            if output is None or len(output) == 0:
                return

            j = None
            try:
                j = json.loads(output)
            except json.JSONDecodeError:
                return

            date = datetime.fromtimestamp(calendar.timegm(datetime.strptime(j["timestamp"], "%Y-%m-%dT%H:%M:%S.%fZ").timetuple()), tz=tz.gettz("UTC")).strftime("%b %d, %Y at %I:%M:%S%p")
            download = j["download"]
            upload = j["upload"]
            ping = j["ping"]
            ip = j["client"]["ip"]
            host = j["server"]["host"]

            if re.search(HOST_PATTERN, host):
                host = re.split(HOST_PATTERN, host)[1]

            params = {
                "date": date,
                "download": download,
                "upload": upload,
                "ping": ping,
                "ip": ip,
                "host": host
            }

            #print(json.dumps(params, indent=2))
            #print("date=" + date, "download=" + str(download), "upload=" + str(upload), "ping=" + str(ping), "ip=" + ip, "host=" + host)
            submit_data(date, ELASTICSEARCH_URL + "/_doc/", params)

        end_time = time.time()
        print("Sleeping", str(SLEEP_TIME - (end_time - start_time)), "seconds..")
        EXIT.wait(max(0, SLEEP_TIME - (end_time - start_time)))
    EXIT.clear()

def quit(signo, _frame):
    print("Exiting sith signal", signo)
    EXIT.set()

if __name__ == "__main__":
    for sig in ("TERM", "HUP", "INT"):
        signal.signal(getattr(signal, "SIG"+sig), quit)
    main()
