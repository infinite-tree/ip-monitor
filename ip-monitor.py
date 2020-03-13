#! /usr/bin/python3

import datetime
import json
import logging
import logging.handlers
import os
from subprocess import Popen, DEVNULL
import sys
import time

from influxdb import InfluxDBClient

LOG_FILE = "/tmp/ip-monitor/ip-monitor.log"
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "ip-monitor.config")


class InfluxWrapper(object):
    def __init__(self, config, log):
        self.Log = log
        self.Config = config
        self.Location = config['location']
        self.Influx = InfluxDBClient(config['host'],
                                     config['port'],
                                     config['login'],
                                     config['password'],
                                     config['database'],
                                     ssl=True,
                                     timeout=60)
        self.Points = []
        self.LastSent = datetime.datetime.now()
        self.Interval = 60
        self.MaxPoints = 250

    def getTime(self):
        now = datetime.datetime.utcnow()
        return now.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    def writePoints(self):
        ret = None

        # drop old points if there are too many
        if len(self.Points) > self.MaxPoints:
            self.Points = self.Points[self.MaxPoints:]

        for x in range(10):
            try:
                ret = self.Influx.write_points(self.Points)
            except Exception as e:
                self.Log.error("Influxdb point failure: %s"%(e))
                ret = 0
            if ret:
                self.Log.info("%s - Sent %d points to Influx"%(datetime.datetime.now(), len(self.Points)))
                self.LastSent = datetime.datetime.now()
                self.Points = []
                return ret

            time.sleep(0.2)

        self.Log.error("%s - Failed to send %d points to Influx: %s"%(datetime.datetime.now(), len(self.Points), ret))
        return ret
    
    def sendMeasurement(self, host, value):
        point = {
            "measurement": "host_online",
            "tags": {
                "location": self.Location,
                "host": host
            },
            "time": self.getTime(),
            "fields": {
                "value": value
            }
        }

        self.Points.append(point)

        now = datetime.datetime.now()
        if len(self.Points) >= self.MaxPoints or (now - self.LastSent).seconds >= self.Interval:
            return self.writePoints()
        return True


class App(object):
    def __init__(self, log):
        self.Log = log
        self.Config = {}
        self.readConfig()
        self.Influx = InfluxWrapper(self.Config['influx'], log)
        self.Hosts = self.Config['hosts']
        self.LoopDelay = 60 * self.Config['ping_frequency']

    def readConfig(self):
        if not os.path.isfile(CONFIG_FILE):
            self.Log.error("Config file '%s' does not exist"%CONFIG_FILE)
            raise Exception("Config file not found")

        with open(CONFIG_FILE, "r") as f:
            self.Config = json.load(f)
    
    def pingAllHosts(self):
        p = {}
        status = {}
        for host, ip in self.Hosts.items():
            p[host] = Popen(['ping', '-n', '-w5', '-c3', ip], stdout=DEVNULL)
            #NOTE: you could set stderr=subprocess.STDOUT to ignore stderr also

        while p:
            for host, proc in p.items():
                if proc.poll() is not None:
                    # ping finished
                    del p[host]
                    status[host] = 0
                    if proc.returncode == 0:
                        status[host] = 1
                        self.Log.debug("host '%s' is online"%host)
                    elif proc.returncode == 1:
                        self.Log.info("Host '%s' did not respond"%host)
                    else:
                        self.Log.error("Unknow error checking host '%s'" % host)
                    
                    self.Influx.sendMeasurement(host, status[host])
                    break

    def run(self):
        # Force an update on first run
        lastUpdate = time.time() - self.LoopDelay

        while True:
            now = time.time()
            if now - lastUpdate > self.LoopDelay:
                self.pingAllHosts()
                lastUpdate = now
            else:
                time.sleep(0.1)


def main():
    log = logging.getLogger('IP_Monitor-Logger')
    log.setLevel(logging.INFO)
    log.setLevel(logging.DEBUG)
    log_file = os.path.realpath(os.path.expanduser(LOG_FILE))
    handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=500000, backupCount=5)

    log.addHandler(handler)
    log.addHandler(logging.StreamHandler())
    log.info("IP-Monitor Starting...")

    try:
        app = App(log)
        app.run()
    except Exception as e:
        log.error("Main loop failed: %s"%(e), exc_info=1)
        sys.exit(1)


if __name__ == "__main__":
    main()