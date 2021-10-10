#!/bin/bash


if [ "$#" -ne 0 ]; then
  source "$1"
fi


mkdir -p "../logs/$destdir"

echo $duser
#port=cat /vortexfs1/home/msantos/Code/pgre/port.txt
host=pn135
port=2984
echo $port
# run transnet
cdir=`pwd`
cd ../app
python Transnet.py -p "../data/$destdir/pfile.poly" -H $host -D $dname -U $duser -X $dpassword -d $destdir -V $vlevels $trans_args -P $port| tee "../logs/$destdir/transnet.log"
cd $cdir

#run matlab
#cdir=`pwd`
#cd ../matlab
#`$matlab -r "transform countries/$destdir;quit;"` | tee "../logs/$destdir/transnet_matlab.log"
#cd $cdir
