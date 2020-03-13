# IP Monitor
Simple script to ping devices and report their status to influxdb 
Display and control system for indoor irrigation controller

## Hardware
Anything that can run python, but the service file is setup for a raspberry pi.

## Installation Notes

You'll need to create an .influxdb.config in your home directory/ It should look like this:

```
{
    "host": "",
    "port": 8086,
    "database": "",
    "login": "",
    "password": "",
    "interval": 60,
    "max_points": 250
}
```

Create a config file with a dictionary of ip's to check:
hosts.json
```
{
    "host1": "192.168.2.1",
    ...
}
```



Then Install the service:

```
pip install -r requirements.txt

sudo mkdir /var/log/ip-monitor

sudo cp ip-monitor.service /etc/systemd/system/
sudo systemctl enable ip-monitor.service
sudo systemctl start ip-monitor.service
```

