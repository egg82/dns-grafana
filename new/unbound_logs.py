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
LEVEL_PATTERN = r'([a-z]+):\s+'
NAME_PATTERN = r'response\s+for\s+([A-Za-z0-9\-\.]+)\.\s+'
TYPE_PATTERN = r'^([A-Z]+)\s+'
REPLY_PATTERN = r'([\d\.:]+)#\d+$'
INSECURE_PATTERN = r'(INSECURE)$'
SECURE_PATTERN = r'sec_status_secure$'

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

    with open('/var/log/unbound.log', 'rt', encoding='utf8') as file:
        for line in tailer.follow(file):
        #while True:
            if finished:
                if not ltype == 'DS' and not ltype == 'DNSKEY':
                    point = Point('query') \
                        .tag('level', level) \
                        .tag('server', server) \
                        .tag('type', ltype) \
                        .tag('dnssec', dnssec) \
                        .field('name', name) \
                        .time(date, WritePrecision.S)

                    WRITE_API.write(INFLUX_BUCKET, INFLUX_ORG, point)
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

            # Line 1
            if date is None:
                if not re.search(DATE_PATTERN, line):
                    continue

                split = re.split(DATE_PATTERN, line)
                date = datetime.fromtimestamp(calendar.timegm(datetime.strptime(str(datetime.now().year) + ' ' + split[1], '%Y %b %d %H:%M:%S').timetuple()), tz=tz.gettz('UTC'))
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