import tailer
import re
import requests
import json
import os
from datetime import datetime
from dateutil import tz
import calendar

DATE_PATTERN = "^([A-Za-z]+\s+\d+\s+\d+:\d+:\d+)\s+"
LEVEL_PATTERN = "\[([A-Z]+)\]\s+"
REMOTE_PATTERN = "^([\d\.:]+):\d+\s+"
TYPE_PATTERN = "\"([A-Z]+)\s+"
NAME_PATTERN = "^[A-Za-z0-9]+\s+([A-Za-z0-9\-\.]+)\.\s+"
DNSSEC_PATTERN = "(true|false)\s+"
CODE_PATTERN = "\"\s+([A-Z]+)\s+"
DURATION_PATTERN = "(\d+\.\d+)s"

ELASTICSEARCH_URL = "http://localhost:9200/coredns"
POST_HEADERS = {
    "User-Agent": "egg82/PyParser",
    "Accept": "application/json",
    "Connection": "close",
    "Accept-Language": "en-US,en;q=0.8",
    "Content-Type": "application/json"
}
FAILURES_FILE = "failures.txt"

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
    with open("/var/log/coredns.log", "rt", encoding="utf8") as file:
        for line in tailer.follow(file):
        #while True:
            #line = file.readline()
            #if not line:
            #    break
            if line is None or len(line) == 0:
                continue

            #print(line)

            if not re.search(DATE_PATTERN, line):
                continue

            split = re.split(DATE_PATTERN, line)
            date = datetime.fromtimestamp(calendar.timegm(datetime.strptime(str(datetime.now().year) + " " + split[1], "%Y %b %d %H:%M:%S").timetuple()), tz=tz.gettz("UTC")).strftime("%b %d, %Y at %I:%M:%S%p")
            line = split[2]

            if not re.search(LEVEL_PATTERN, line):
                continue

            split = re.split(LEVEL_PATTERN, line)
            level = split[1]
            line = split[2]

            if not re.search(REMOTE_PATTERN, line):
                continue

            split = re.split(REMOTE_PATTERN, line)
            remote = split[1]
            line = split[2]

            if not re.search(TYPE_PATTERN, line):
                continue

            split = re.split(TYPE_PATTERN, line)
            ltype = split[1]
            line = split[2]

            if not re.search(NAME_PATTERN, line):
                continue

            split = re.split(NAME_PATTERN, line)
            name = split[1]
            line = split[2]

            if not re.search(DNSSEC_PATTERN, line):
                continue

            split = re.split(DNSSEC_PATTERN, line)
            dnssec = split[1] == "true"
            line = split[2]

            if not re.search(CODE_PATTERN, line):
                continue

            split = re.split(CODE_PATTERN, line)
            code = split[1]
            line = split[2]

            if not re.search(DURATION_PATTERN, line):
                continue

            split = re.split(DURATION_PATTERN, line)
            duration = float(split[1]) * 1000.0

            params = {
                "date": date,
                "level": level,
                "remote": remote,
                "type": ltype,
                "name": name,
                "dnssec": dnssec,
                "code": code,
                "duration": duration
            }

            #print(json.dumps(params, indent=2))
            #print("date=" + date, "level=" + level, "remote=" + remote, "type=" + ltype, "name=" + name, "dnssec=" + str(dnssec), "code=" + code, "duration=" + str(duration))
            submit_data(remote + ";" + name, ELASTICSEARCH_URL + "/_doc/", params)

if __name__ == '__main__':
    main()