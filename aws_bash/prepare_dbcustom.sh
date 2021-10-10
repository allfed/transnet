#!/bin/bash

if [ "$#" -ne 0 ]; then
  # load the appropriate config file
  source "$1"
fi

mkdir -p "../data/$destdir"

if [ ! -z ${ddump_url+x} ]
  then
        echo "Downloading $ddump_url"
        wget "$ddump_url" -O "../data/$destdir/ddump.pbf"
        ddump="../data/$destdir/ddump.pbf"
  else
  echo "Using dump file $ddump"
fi

#download poly files, move them to appropriate locations
if [ ! -z ${pfile_url+x} ]
  then
    echo "Downloading $pfile_url"
    wget "$pfile_url" -O "../data/planet/$destdir/pfile.poly"

    echo "Downloading Poly files for all countries in continent"
    ping download.geofabrik.de -c 3 #this helps for some reason...
    wget -A poly -r -l 1 -nd http://download.geofabrik.de/$continent/
    set -o errexit -o nounset
    for file in *.poly
    do
      dir="${file%.poly}"
      mkdir -p -- "../data/${continent}/${dir}"
      mv -- "$file" "../data/${continent}/${dir}/pfile.poly"
    done

  else
    echo "Using existing poly files"
fi

echo "1. Drop the database"
psql -U $duser -h localhost -c "DROP DATABASE $dname;"

echo "2. create new database"
psql -U $duser -d transnet_template -h localhost -c "CREATE DATABASE $dname WITH TEMPLATE = transnet_template;"

echo "3. filter everything tagged with power=* OR substation=* and any routes with route=power using Osmium"
echo "see https://osmcode.org/osmium-tool/manual.html for help with osmium "

osmium tags-filter $ddump nwr/substation nwr/power r/route=power -o "../data/$destdir/power_extract.pbf" --overwrite -v

echo "4. import to postgresql database"

osm2pgsql -r pbf --username=$duser -d $dname -E 3857 -k -s -C 1000 -v --host='localhost' --port='5432' --style ../util/power.style "../data/$destdir/power_extract.pbf"
