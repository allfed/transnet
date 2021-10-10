ddump = /data/home/ec2-user/transnet/data/north-america/north-america.ddump
pfile = /data/home/ec2-user/transnet/data/north-america/us/pfile.poly


osmium tags-filter $ddump nwr/substation nwr/power r/route=power -o "../data/$destdir/power_extract.pbf" --overwrite -v

osmium extract -p paris-polygon.poly france.pbf -o paris.pbf
