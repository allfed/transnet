#!/bin/bash
# launch a complete Transnet run

if [ "$#" -ne 0 ]; then
  # load the appropriate config file
  source "$1"
fi

mkdir -p "../logs/$destdir"
portfilename=/vortexfs1/home/msantos/Code/pgre/port.txt
hostfilename=/vortexfs1/home/msantos/Code/pgre/host.txt
read port < $portfilename
read host < $hostfilename
echo Port
echo $port
echo Host
echo $host

# run transnet
cdir=`pwd`
cd ../app
mkdir -p "../logs/planet/$destdir"
python Transnet.py -p "/vortexfs1/home/msantos/Code/transnet/data/$destdir/pfile.poly" -c $continent -H $host -P $port -D $dname -U $duser -X $dpassword -d $destdir -V $vlevels $trans_args | tee "/vortexfs1/home/msantos/Code/transnet/logs/$destdir/transnet.log"

