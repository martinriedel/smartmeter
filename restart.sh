#!/bin/bash
sudo systemctl stop smartmeter.service
sudo systemctl start smartmeter.service
echo "restart of smartmeter completed"
