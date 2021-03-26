import tailer
import re
from datetime import datetime
from dateutil import tz
import calendar

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

INFLUX_URL = 'http://127.0.0.1:8086'
INFLUX_TOKEN = '$$$ INFLUX-TOKEN $$$'
INFLUX_ORG = 'dns'
INFLUX_BUCKET = 'dns'

CLIENT = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN)
WRITE_API = CLIENT.write_api(write_options=SYNCHRONOUS)

DATE_PATTERN = r'^([A-Za-z]+\s+\d+\s+\d+:\d+:\d+)\s+'
HOST_PATTERN = r'^([A-Za-z0-9\-\.]+)\s+'
LEVEL_PATTERN = r'\[([A-Z]+)\]\s+'
REMOTE_PATTERN = r'^([\d\.:]+):\d+\s+'
TYPE_PATTERN = r'"([A-Z0-9]+)\s+'
NAME_PATTERN = r'^[A-Za-z0-9]+\s+([A-Za-z0-9\-\.]+)\.\s+'
DNSSEC_PATTERN = r'(true|false)\s+'
CODE_PATTERN = r'"\s+([A-Z]+)\s+'
DURATION_PATTERN = r'(\d+\.\d+)s'

def main():
    with open('/var/log/coredns.log', 'rt', encoding='utf8') as file:
        for line in tailer.follow(file):
        #while True:
            #line = file.readline()
            #if not line:
            #    break
            if line is None or len(line) == 0:
                continue

            if not re.search(DATE_PATTERN, line):
                continue

            split = re.split(DATE_PATTERN, line)
            date = datetime.fromtimestamp(calendar.timegm(datetime.strptime(str(datetime.now().year) + ' ' + split[1], '%Y %b %d %H:%M:%S').timetuple()), tz=tz.gettz('UTC'))
            line = split[2]

            if not re.search(HOST_PATTERN, line):
                continue

            split = re.split(HOST_PATTERN, line)
            host = split[1]
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
            dnssec = split[1] == 'true'
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

            point = Point('query') \
                .tag('host', host) \
                .tag('level', level) \
                .tag('remote', remote) \
                .tag('type', ltype) \
                .tag('dnssec', dnssec) \
                .tag('code', code) \
                .field('name', name) \
                .field('duration', duration) \
                .time(date, WritePrecision.S)

            WRITE_API.write(INFLUX_BUCKET, INFLUX_ORG, point)

if __name__ == '__main__':
    main()