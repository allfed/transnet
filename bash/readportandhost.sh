portfilename=/vortexfs1/home/msantos/Code/pgre/port.txt
hostfilename=/vortexfs1/home/msantos/Code/pgre/host.txt
read port < $portfilename
read host < $hostfilename
# reading each line
echo Port
echo $port
echo Host
echo $host
