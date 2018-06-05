#!/bin/bash
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
# 
# A script to set up a notebook's $HOME directory.

# Set up Jupyter notebooks
mkdir -p $NOTEBOOK_HOME
mkdir -p $HOME/reference-notebooks
# Copy the introduction and reference notebooks, overwriting the existing files
cp -f '/pru-python/notebooks/Introduction And Orientation.ipynb' $HOME
cp -f -r /pru-python/notebooks/* $HOME/reference-notebooks/.

# Set up logging
mkdir -p $LOGGER_HOME
mkdir -p $LOGGER_HOME/logs
# Copy the logging config file but do NOT overwrite the existing file
cp -n /pru-python/config/logging.yaml $LOGGER_HOME/logging.yaml

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

