#!/bin/sh
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
#

# Set up logging
mkdir -p $LOGGER_HOME
mkdir -p $LOGGER_HOME/logs

# NOTE alpine does not support cp -n (no clobber)
cp /pru-python/config/logging.yaml $LOGGER_HOME/logging.yaml

# Create data directories
mkdir -p $DATA_HOME
mkdir -p $DATA_HOME/airports
mkdir -p $DATA_HOME/airports/stands
mkdir -p $DATA_HOME/airspaces
mkdir -p $DATA_HOME/upload
mkdir -p $DATA_HOME/upload/cpr
mkdir -p $DATA_HOME/upload/fr24
mkdir -p $DATA_HOME/upload/apds
mkdir -p $DATA_HOME/products
mkdir -p $DATA_HOME/refined
mkdir -p $DATA_HOME/merged
mkdir -p $DATA_HOME/analysis
mkdir -p $DATA_HOME/fleet_data
mkdir -p $DATA_HOME/backups

CMD=$1
echo $CMD
"$@"
