#!/bin/bash
ping download.geofabrik.de -c 3 #this helps for some reason...


if [ "$#" -ne 0 ]; then
  # load the appropriate config file
  source "$1"
fi

if [ ! -z ${pfile_url+x} ]
  then
	echo "Downloading $pfile_url"
	wget "$pfile_url" -O "../data/planet/$destdir/pfile.poly"
fi


# ./loadContinentsPolys.sh ../configs/australia-oceania.conf
# ./loadContinentsPolys.sh ../configs/europe.conf
# ./loadContinentsPolys.sh ../configs/south-america.conf
# ./loadContinentsPolys.sh ../configs/africa.conf
# ./loadContinentsPolys.sh ../configs/north-america.conf
# ./loadContinentsPolys.sh ../configs/central-america.conf
# ./loadContinentsPolys.sh ../configs/russia.conf
# ./loadContinentsPolys.sh ../configs/asia.conf


