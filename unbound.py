import tailer
import re
import requests
import json
import os
from datetime import datetime
from dateutil import tz
import calendar

DATE_PATTERN = "^([A-Za-z]+\s+\d+\s+\d+:\d+:\d+)\s+"
LEVEL_PATTERN = "([a-z]+):\s+"
NAME_PATTERN = "response\s+for\s+([A-Za-z0-9\-\.]+)\.\s+"
TYPE_PATTERN = "^([A-Z]+)\s+"
REPLY_PATTERN = "([\d\.:]+)#\d+$"
INSECURE_PATTERN = "(INSECURE)$"
SECURE_PATTERN = "sec_status_secure$"

ELASTICSEARCH_URL = "http://localhost:9200/unbound"
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
    reset = False
    finished = False
    date = None
    level = None
    name = None
    ltype = None
    dnssec = False
    dnssec_set = False
    server = None

    with open("/var/log/unbound.log", "rt", encoding="utf8") as file:
        for line in tailer.follow(file):
        #while True:
            if finished:
                if not ltype == "DS" and not ltype == "DNSKEY":
                    params = {
                        "date": date,
                        "level": level,
                        "server": server,
                        "type": ltype,
                        "name": name,
                        "dnssec": dnssec
                    }

                    #print(json.dumps(params, indent=2))
                    #print("date=" + date, "level=" + level, "server=" + str(server), "type=" + ltype, "name=" + name, "dnssec=" + str(dnssec))
                    submit_data(server + ";" + name, ELASTICSEARCH_URL + "/_doc/", params)
                reset = True

            if reset:
                date = None
                level = None
                name = None
                ltype = None
                dnssec = False
                dnssec_set = False
                server = None
                reset = False
                finished = False

            #line = file.readline()
            #if not line:
            #    break
            if line is None or len(line) == 0:
                continue

            #print(line)

            # Line 1
            if date is None:
                if not re.search(DATE_PATTERN, line):
                    continue

                split = re.split(DATE_PATTERN, line)
                date = datetime.fromtimestamp(calendar.timegm(datetime.strptime(str(datetime.now().year) + " " + split[1], "%Y %b %d %H:%M:%S").timetuple()), tz=tz.gettz("UTC")).strftime("%b %d, %Y at %I:%M:%S%p")
                line = split[2]

            if level is None:
                if not re.search(LEVEL_PATTERN, line):
                    reset = True
                    continue

                split = re.split(LEVEL_PATTERN, line)
                level = split[1]
                line = split[2]

            if name is None:
                if not re.search(NAME_PATTERN, line):
                    reset = True
                    continue

                split = re.split(NAME_PATTERN, line)
                name = split[1]
                line = split[2]

                if not re.search(TYPE_PATTERN, line):
                    reset = True
                    continue

                split = re.split(TYPE_PATTERN, line)
                ltype = split[1]
                continue # EOL

            # Line 2
            if server is None:
                if not re.search(REPLY_PATTERN, line):
                    reset = True
                    continue

                split = re.split(REPLY_PATTERN, line)
                server = split[1]
                continue # EOL

            if not dnssec_set:
                if re.search(INSECURE_PATTERN, line):
                    dnssec = False
                    dnssec_set = True
                    finished = True # Done
                    continue
                if re.search(SECURE_PATTERN, line):
                    dnssec = True
                    dnssec_set = True
                    finished = True # Done
                    continue

            continue # Skip line

if __name__ == '__main__':
    main()