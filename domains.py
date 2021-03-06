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
import validators

HOME = str(Path.home())
HOST_PATTERN = "([a-zA-Z0-9\-\.]+)"

ELASTICSEARCH_URL = "http://localhost:9200/domains"
POST_HEADERS = {
    "User-Agent": "egg82/PyParser",
    "Accept": "application/json",
    "Connection": "close",
    "Accept-Language": "en-US,en;q=0.8",
    "Content-Type": "application/json"
}
GET_HEADERS = {
    "User-Agent": "egg82/PyParser",
    "Accept": "text/html",
    "Connection": "close",
    "Accept-Language": "en-US,en;q=0.8"
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

def delete_data(url, params):
    req = requests.post(url, headers=POST_HEADERS, json=params)
    if req.status_code < 200 or req.status_code >= 300:
        print("Got status code " + str(req.status_code) + " for " + url)
    else:
        print("Deleted " + url + "!")

def get_data(url):
    req = requests.get(url, headers=GET_HEADERS)
    if req.status_code < 200 or req.status_code >= 300:
        print("Got status code " + str(req.status_code) + " for " + url)
        return None
    else:
        return req.text

def get_text(request):
    text = request.text
    if text is None:
        return None
    
    try:
        return json.loads(text)
    except ValueError:
        return None
    return None

def data_exists(host):
    tries = 0

    params = {
        "query": {
            "term": {
                "host": {
                    "value": host
                }
            }
        }
    }

    response = None
    while True:
        req = requests.get(ELASTICSEARCH_URL + "/_search", headers=POST_HEADERS, json=params)
        if req.status_code == 429:
            time.sleep(0.5)
        else:
            response = get_text(req)
            if not response is None:
                break
            elif response is None and tries >= 3:
                break
            else:
                tries += 1
                time.sleep(3.0)
    
    if response is None:
        print("Failed to get response, skipping..")
        add_failure(json.dumps(params))
        return False

    if response["hits"]["total"]["value"] > 0:
        return True
    return False

def parse_data(text, domain_type):
    date = datetime.fromtimestamp(calendar.timegm(datetime.utcnow().timetuple()), tz=tz.gettz("UTC")).strftime("%Y-%m-%d %H:%M:%S")

    for line in text.splitlines():
        line = line.strip()
        if len(line) == 0 or line.startswith("[") or line.startswith("!") or line.startswith("-"):
            continue

        if not re.search(HOST_PATTERN, line):
            continue
        
        host = None
        hosts = re.split(HOST_PATTERN, line)
        for h in hosts:
            h = h.strip()
            if len(h) == 0 or h == "0.0.0.0" or h == "href" or h.startswith("http"):
                continue
            if not validators.domain(h):
                continue
            host = h
        
        if host is None:
            continue

        if data_exists(host):
            print("Domain " + host + " already exists, skipping..")
            continue

        params = {
            "host": host,
            "type": domain_type,
            "date": date
        }

        #print(json.dumps(params, indent=2))
        #print("host=" + host)
        submit_data(host, ELASTICSEARCH_URL + "/_doc/", params)

def main():
    params = {
        "query": {
            "match_all": {}
        }
    }
    delete_data(ELASTICSEARCH_URL + "/_delete_by_query?conflicts=proceed", params)

    # Malware

    result = get_data("https://gitcdn.xyz/cdn/NanoMeow/MDLMirror/80e37024e4d7ef3bf27518abeac2250caba9a17e/hosts.txt")
    if not result is None:
        parse_data(result, "Malware")
    
    result = get_data("https://mirror.cedia.org.ec/malwaredomains/justdomains")
    if not result is None:
        parse_data(result, "Malware")
    
    result = get_data("https://raw.githubusercontent.com/Spam404/lists/master/adblock-list.txt")
    if not result is None:
        parse_data(result, "Malware")
    
    result = get_data("https://raw.githubusercontent.com/blocklistproject/Lists/master/malware.txt")
    if not result is None:
        parse_data(result, "Malware")
    
    # Adult content/NSFW

    result = get_data("https://raw.githubusercontent.com/blocklistproject/Lists/master/porn.txt")
    if not result is None:
        parse_data(result, "Adult")
    
    result = get_data("https://raw.githubusercontent.com/blocklistproject/Lists/master/drugs.txt")
    if not result is None:
        parse_data(result, "Drugs")
    
    result = get_data("https://raw.githubusercontent.com/blocklistproject/Lists/master/gambling.txt")
    if not result is None:
        parse_data(result, "Gambling")
    
    result = get_data("https://raw.githubusercontent.com/blocklistproject/Lists/master/piracy.txt")
    if not result is None:
        parse_data(result, "Piracy")
    
    result = get_data("https://raw.githubusercontent.com/blocklistproject/Lists/master/torrent.txt")
    if not result is None:
        parse_data(result, "Piracy")
    
    # General Protection
    result = get_data("https://raw.githubusercontent.com/blocklistproject/Lists/master/fraud.txt")
    if not result is None:
        parse_data(result, "Fraud")
    
    result = get_data("https://raw.githubusercontent.com/blocklistproject/Lists/master/phishing.txt")
    if not result is None:
        parse_data(result, "Phishing")

if __name__ == "__main__":
    main()
