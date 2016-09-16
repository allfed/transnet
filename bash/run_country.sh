#!/bin/bash
# launch a complete Transnet run


if [ "$#" -ne 0 ]; then
  # load the appropriate config file
  source "$1"
fi

# matlab directory epezhman
#matlab='/usr/local/bin/matlab'

# matlab directory remote
matlab='/usr/bin/matlab'

mkdir -p "../logs/$destdir"

# run transnet
cdir=`pwd`
cd ../app
python Transnet.py -p "../data/$destdir/pfile.poly" -D $dname -U $duser -X $dpassword -d $destdir -V $vlevels $trans_args | tee "../logs/$destdir/transnet.log"
cd $cdir

# run matlab
#cdir=`pwd`
#cd ../matlab
#`$matlab -r "transform countries/$destdir;quit;"` | tee "../logs/$destdir/transnet_matlab.log"
#cd $cdir
