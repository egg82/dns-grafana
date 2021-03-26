import subprocess
import ujson
import re
from datetime import datetime
from dateutil import tz
import calendar
import time
from threading import Event
import signal
from pathlib import Path

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

from . settings import INFLUX_URL
from . settings import INFLUX_TOKEN
from . settings import INFLUX_BUCKET
from . settings import INFLUX_ORG

CLIENT = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN)
WRITE_API = CLIENT.write_api(write_options=SYNCHRONOUS)

HOME = str(Path.home())
SERVER_PATTERN = r'^([a-zA-Z0-9\-\.]+):\d+$'

SLEEP_TIME = 1200.0 # 20 mins

EXIT = Event()

def main():
    while not EXIT.is_set():
        start_time = time.time()
        for i in range(0, 3):
            result = subprocess.run([HOME + '/.local/bin/speedtest-cli', '--json', '--secure'], stdout=subprocess.PIPE)
            output = result.stdout.decode('UTF-8')

            if output is None or len(output) == 0:
                return

            j = None
            try:
                j = ujson.loads(output)
            except ujson.JSONDecodeError:
                return

            date = datetime.fromtimestamp(calendar.timegm(datetime.strptime(j['timestamp'], '%Y-%m-%dT%H:%M:%S.%fZ').timetuple()), tz=tz.gettz('UTC'))
            download = j['download']
            upload = j['upload']
            ping = j['ping']
            ip = j['client']['ip']
            server = j['server']['host']

            if re.search(SERVER_PATTERN, server):
                server = re.split(SERVER_PATTERN, server)[1]

            point = Point('result') \
                .tag('server', server) \
                .tag('ip', ip) \
                .field('ping', ping) \
                .field('download', download) \
                .field('upload', upload) \
                .time(date, WritePrecision.S)

            WRITE_API.write(INFLUX_BUCKET, INFLUX_ORG, point)

        end_time = time.time()
        print('Sleeping', str(SLEEP_TIME - (end_time - start_time)), 'seconds..')
        EXIT.wait(max(0, SLEEP_TIME - (end_time - start_time)))
    EXIT.clear()

def quit(signo, _frame):
    print('Exiting sith signal', signo)
    EXIT.set()

if __name__ == '__main__':
    for sig in ('TERM', 'HUP', 'INT'):
        signal.signal(getattr(signal, 'SIG'+sig), quit)
    main()
