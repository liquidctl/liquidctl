# liquidctlfan a wrapper script for liquidctl to control your fans
When I built my first water-cooled PC a few months ago, using Linux, I thought it would be easy to control or regulate it. I quickly found liqduictl on github and after a few weeks I could control my NZXT X73 under Linux. Thanks a lot for that!
Unfortunately I found out that I couldn't control the fans in relation to the CPU temperature. (see https://github.com/jonasmalacofilho/liquidctl/issues/118)

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

## Configuration
In my PC I have three fans on the radiator and one case fan on a NZXT Grid+ V3 controller. The ProductID can be found out via liquidctl.

Under PRID you have to enter the ID of the controller to be controlled:
`PRID="0x1711"`

The CPU temperatures CPUT1...4 are the limit values of the CPU temperature.
CPUT1 is the lowest and CPUT4 the highest. The values are stored in degrees Celsius and must be adjusted if Fahrenheit is to be used.
```
CPUT1="50.0" # 50.0 °C
CPUT2="60.0" # 60.0 °C
CPUT3="70.0" # 70.0 °C
CPUT4="80.0" # 80.0 °C
```
The fans are configured via the following setpoints FANT0...FANT4. The setpoints are in percent.
```
FANT0="30" # 30 %
FANT1="40" # 40 %
FANT2="50" # 50 %
FANT3="80" # 80 %
FANT4="100" #100 %
```
The SLTIME parameter is used to set the waiting time in seconds between control interventions.

`SLTIME="10" # 10 s`

Via SYSLOG the logging into the syslog is activated. With 1 the output is transferred to the syslog. With 0 STDOUT.

```
SYSLOG="1" # Enable Syslog
SYSLOG="0" # Only STDOUT
```

## Systemd
In the directory systemd you will find the unit file.
Copy the file with root access liquidctlfan.service into /etc/systemd/system.

Use the following commands to reload the configuration, load the daemon at startup, start or stop the daemon.

```
systemctl daemon reload
systemctl enable liquidctlfan.service
systemctl start liquidctlfan.service
systemctl stop liquidctlfan.service
```
