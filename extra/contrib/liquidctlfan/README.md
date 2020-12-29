# liquidctlfan a wrapper script for liquidctl to control your fans
When I built my first water-cooled PC a few months ago, using Linux, I thought it would be easy to control or regulate it. I quickly found liquidctl on Github and after a few weeks I could control my NZXT X73 under Linux. Thanks a lot for that!
Unfortunately I found out that I couldn't control the fans in relation to the CPU temperature. (see https://github.com/liquidctl/liquidctl/issues/118)

## Components
liquidctlfan - Wrapper script as a small demon
systemd unit file - Unit file for integration into systemd

## Prerequisites
The tools bc, sensors, liquidctl and logger must be installed.
Sensors must receive a basic configuration before it can be used. Please use sensors-detect for this. The setup takes some time depending on the system. For example, after installation, a Ryzen 9 looks like this:
```
k10temp-pci-00c3
Adapter: PCI adapter
Tdie: +42.0°C (high = +70.0°C)
Tctl: +42.0°C
```
The script expects a line like Tdie.

The script has been tested under Linux Mint 19.3.

## Installation
Copy the file liquidctlfan into the directory "/usr/local/bin/" and set the permissions if necessary.

## Configuration and usage
```
Usage: ./liquidctlfan
	-p | --product is the product id of your fan controller (e.g. 0x1711) [*]
	-u | --unit Celsius or Fahrenheit (e.g. c|C|Celsius|f|F|Fahrenheit) [*]
	-ct1| --cputemp1 CPU temperature threshold value lowest (e.g. 50.0) [*]
	-ct2| --cputemp2 CPU temperature threshold value (e.g. 60.0) [*]
	-ct3| --cputemp3 CPU temperature threshold value (e.g. 70.0) [*]
	-ct4| --cputemp4 CPU temperature threshold value highest (e.g. 80.0) [*]
	-f0|--fan0 Fan setpoint in percent (e.g. 30) [*]
	-f1|--fan1 Fan setpoint in percent (e.g. 40) [*]
	-f2|--fan2 Fan setpoint in percent (e.g. 50) [*]
	-f3|--fan3 Fan setpoint in percent (e.g. 80) [*]
	-f4|--fan4 Fan setpoint in percent (e.g. 100) [*]
	-i|--interval CPU temperature check time in seconds (e.g. 10) [*]
	-l|--log Enable syslog logging (e.g. enable|disable|ENABLE|DISABLE) [*]
        -a|--about Show about message
        -h|--help Show this message

 [*] mandatory parameter
```
A normal call could be ...

`./liquidctlfan -p 0x1711 -u c -ct1 50.0 -ct2 60.0 -ct3 70.0 -ct4 80.0 -f0 30 -f1 40 -f2 50 -f3 80 -f4 100 -i 10 -l disable`

If it is not desired to pass parameters, all parameters can be stored permanently in the script. Just activate the parameters in the configuration area of the script (remove #). 
```
### Enable configuration to disable parameter handling ####
### Product ID of HUE Grid
#PRID="0x1711"
##Unit Celsius C or Fahrenheit F
#UNIT="C"
### CPU temperature threshold values
#CPUT1="50.0"
#CPUT2="60.0"
#CPUT3="70.0"
#CPUT4="80.0"
### FAN setpoints
#FAN0="30"
#FAN1="40"
#FAN2="50"
#FAN3="80"
#FAN4="100"
###Interval check time
#SLTIME="10"
###Enable Syslog
#SYSLOG="enable"
###########################################################
```
## systemd
In the directory systemd you will find the unit file.
Copy the file with root access liquidctlfan.service into /etc/systemd/system.

Please regard if the parameters are to be transferred or if the stored parameters are to be taken over. The appropriate line must be activated.
```
[Unit]
Description=liquidctl Fan Control
After=liquidcfg.service

[Service]
## Fixed configuration
#ExecStart=/usr/local/bin/liquidctlfan
## Handover parameters
ExecStart=/usr/local/bin/liquidctlfan -p 0x1711 -u c -ct1 50.0 -ct2 60.0 -ct3 70.0 -ct4 80.0 -f0 30 -f1 40 -f2 50 -f3 80 -f4 100 -i 10 -l enable
Restart=on-failure

[Install]
WantedBy=multi-user.target 
```
Use the following commands to reload the configuration, load the daemon at startup, start or stop the daemon.

```
systemctl daemon reload
systemctl enable liquidctlfan.service
systemctl start liquidctlfan.service
systemctl stop liquidctlfan.service
```


