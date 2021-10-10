source "$1"

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


