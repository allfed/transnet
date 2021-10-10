#!/bin/bash
#SBATCH --partition=compute         # Queue selection
#SBATCH --job-name=rcrussia       # Job name
#SBATCH --mail-type=END             # Mail events (BEGIN, END, FAIL, ALL)
#SBATCH --mail-user=orgmanrivers@gmail.com  # Where to send mail
#SBATCH --ntasks=1                  # Run on a single CPU
#SBATCH --mem=32gb                   # Job memory request
#SBATCH --time=22:00:00             # Time limit hrs:min:sec
#SBATCH --output=runcon_%j.log  # Standard output/error

pwd; hostname; date

#module load python3/3.6.5                  # Load the python module
module load anaconda/5.1


#load config
source /vortexfs1/home/msantos/Code/transnet/configs/russia.conf

mkdir -p "../logs/planet/$destdir"

source /vortexfs1/apps/anaconda-5.1/etc/profile.d/conda.sh
conda init bash
conda activate /vortexfs1/home/msantos/.conda/envs/myenv

echo $duser
echo $duser
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
/vortexfs1/home/msantos/.conda/envs/myenv/bin/python Transnet.py -p "/vortexfs1/home/msantos/Code/transnet/data/$destdir/pfile.poly" -c $continent -H $host -P $port -D $dname -U $duser -X $dpassword -d $destdir -V $vlevels $trans_args | tee "/vortexfs1/home/msantos/Code/transnet/logs/$destdir/transnet.log"

date
