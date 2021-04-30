
echo "1. Drop the database"
psql -U postgres -h localhost -c "DROP DATABASE test;"

echo "2. create new database"
psql -U postgres -d transnet_template -h localhost -c "CREATE DATABASE test WITH TEMPLATE = transnet_template;"

echo "3. filter all power nodes/ways of relations tagged with power=*"
# osmosis --read-xml file="../data/great-britain/mapQueen.osm" --tag-filter accept-relations substation=* power=* --tag-filter accept-ways substation=* power=* --tag-filter accept-nodes substation=* power=* --used-node --buffer --bounding-polygon file="../data/great-britain/pfile.poly" completeRelations=yes --write-pbf file="../data/great-britain/power_extract1map.pbf"
osmosis --read-xml file="../data/great-britain/mapQueen.osm" --used-node --buffer --bounding-polygon file="../data/great-britain/pfile.poly" completeRelations=yes --write-pbf file="../data/great-britain/power_extract1map.pbf"

echo "4. filter all relations tagged with route=power"
osmosis --read-xml file="../data/great-britain/mapQueen.osm" --tag-filter accept-relations route=power route=substation --used-way --used-node --buffer --bounding-polygon file="../data/great-britain/pfile.poly"  completeRelations=yes completeWays=yes --write-pbf file="../data/great-britain/power_extract2map.pbf"

echo "5. filter all ways and its corresponding nodes tagged with power=*"
osmosis --read-xml file="../data/great-britain/mapQueen.osm" --tag-filter accept-ways substation=* power=* --used-node --buffer --bounding-polygon file="../data/great-britain/pfile.poly" completeWays=yes  --write-pbf file="../data/great-britain/power_extract3map.pbf"

echo "6. merge all extracts"
osmosis --read-pbf file="../data/great-britain/power_extract1map.pbf" --read-pbf file="../data/great-britain/power_extract2map.pbf" --merge --write-pbf file="../data/great-britain/power_extract12map.pbf"
osmosis --read-pbf file="../data/great-britain/power_extract12map.pbf" --read-pbf file="../data/great-britain/power_extract3map.pbf" --merge --write-pbf file="../data/great-britain/power_extractmap.pbf"

echo "7. import to postgresql database"
osm2pgsql -r pbf --username=postgres -d test -E 3857 -k -s -C 1000 -v --host='localhost' --port='5432' --style ../util/power.style "../data/great-britain/power_extractmap.pbf"
