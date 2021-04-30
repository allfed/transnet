
echo "1. Drop the database"
psql -U postgres -h localhost -c "DROP DATABASE test;"

echo "2. create new database"
psql -U postgres -d transnet_template -h localhost -c "CREATE DATABASE test WITH TEMPLATE = transnet_template;"

echo "3. filter all power nodes/ways of relations tagged with power=*"
osmosis --read-xml file="../data/great-britain/mapQueen.osm" --tag-filter accept-relations substation=* power=* --tag-filter accept-ways substation=* power=* --tag-filter accept-nodes substation=* power=* --used-node --buffer --bounding-polygon file="../data/great-britain/pfile.poly" completeRelations=yes --write-pbf file="../data/great-britain/power_extract1map.pbf"

echo "7. import to postgresql database"
osm2pgsql -r pbf --username=postgres -d test2 -E 3857 -k -s -C 1000 -v --host='localhost' --port='5432' --style ../util/power.style "../data/great-britain/power_extract1map.pbf"
