#!/bin/bash

if [ "$#" -ne 0 ]; then
  # load the appropriate config file
  source "$1"
fi

mkdir -p "../data/$destdir"

echo "1. Drop the database"
psql -U $duser -h localhost -c "DROP DATABASE $dname;"

echo "2. create new database"
psql -U $duser -d transnet_template -h localhost -c "CREATE DATABASE $dname WITH TEMPLATE = transnet_template;"


echo "4. import to postgresql database"

osm2pgsql -r pbf --username=$duser -d $dname -E 3857 -k -s -C 1000 -v --host='localhost' --port='5432' --style ../util/power.style "../data/$destdir/power_extract.pbf"
