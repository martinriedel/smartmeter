#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

chmod +x $SCRIPT_DIR/smartmeter.py

PIP3=$(which pip3)

echo 'Installing packages'
if [ -z $PIP3 ]; then
  apt update
  apt -y install python3-pip
  apt -y install python3-paho-mqtt
  apt -y install python3-serial

fi
pip3 install -r requirements.txt
echo 'Packages install completed'

if systemctl --type=service --state=running | grep -Fq 'smartmeter.service'; then
  echo 'Uninstall smartmeter.service'
  systemctl stop smartmeter.service
  systemctl disable smartmeter.service
  rm /etc/systemd/system/smartmeter.service
  systemctl daemon-reload
  systemctl reset-failed
  echo 'Uninstallation of smartmeter.service completed'
fi

cat << EOF | tee /etc/systemd/system/smartmeter.service
[Unit]
Description=smartmeter Service
After=multi-user.target
[Service]
Type=simple
Restart=always
ExecStart=/usr/bin/python3 ${SCRIPT_DIR}/smartmeter.py
[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable smartmeter.service
systemctl start smartmeter.service
systemctl status smartmeter.service

echo 'Installation of smartmeter completed'