
echo "please enter database password: "
read -s pass
export PGPASSWORD=$pass

#load config
source /data/home/ec2-user/transnet/configs/north-america.conf

mkdir -p "../logs/$destdir"

#conda activate /data/home/ec2-user/anaconda3/envs/myenv

portfilename=/data/home/ec2-user/pgre/pgre/port_aws.txt
hostfilename=/data/home/ec2-user/pgre/pgre/host_aws.txt
read port < $portfilename
read host < $hostfilename
echo Port
echo $port
echo Host
echo $host
# run transnet
cdir=`pwd`
cd ../app
echo $destdir
touch ../logs/$destdir/transnet.log
python Transnet.py -p "../data/$destdir/pfile.poly" -c $continent -H $host -P $port -D $dname -U $duser -X $pass -d $destdir -V $vlevels $trans_args | tee "../logs/$destdir/transnet.log"

#date
