#!/bin/bash
if systemctl --type=service --state=running | grep -Fq 'smartmeter.service'; then
  echo 'Uninstall smartmeter.service'
  systemctl stop smartmeter.service
  systemctl disable smartmeter.service
  rm /etc/systemd/system/smartmeter.service
  systemctl daemon-reload
  systemctl reset-failed
  echo 'Uninstallation of smartmeter.service completed'
fi
