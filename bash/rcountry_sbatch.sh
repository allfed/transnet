#!/bin/bash
#SBATCH --partition=compute         # Queue selection
#SBATCH --job-name=rcireland       # Job name
#SBATCH --mail-type=END             # Mail events (BEGIN, END, FAIL, ALL)
#SBATCH --mail-user=orgmanrivers@gmail.com  # Where to send mail
#SBATCH --ntasks=1                  # Run on a single CPU
#SBATCH --mem=32gb                   # Job memory request
#SBATCH --time=05:00:00             # Time limit hrs:min:sec
#SBATCH --output=runcountry_%j.log  # Standard output/error

pwd; hostname; date

#module load python3/3.6.5                  # Load the python module
module load anaconda/5.1


#load config
source /vortexfs1/home/msantos/Code/transnet/configs/ireland-and-northern-ireland.conf

mkdir -p "../logs/$destdir"

source /vortexfs1/apps/anaconda-5.1/etc/profile.d/conda.sh
conda init bash
conda activate /vortexfs1/home/msantos/.conda/envs/myenv
mkdir -p "../logs/$destdir"

echo $duser
#port=cat /vortexfs1/home/msantos/Code/pgre/port.txt
host=pn135
port=2984
echo $port
# run transnet
cdir=`pwd`
cd ../app
/vortexfs1/home/msantos/.conda/envs/myenv/bin/python Transnet.py -p "/vortexfs1/home/msantos/Code/transnet/data/$destdir/pfile.poly" -H $host -P $port -D $dname -U $duser -X $dpassword -d $destdir -V $vlevels $trans_args | tee "/vortexfs1/home/msantos/Code/transnet/logs/$destdir/transnet.log"

date
