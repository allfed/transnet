echo "please enter database password: "
read -s pass
export PGPASSWORD=$pass

cd ../data/north-america
psql --host=geomagnetic-storm-model.cqicqdey3ckh.us-east-2.rds.amazonaws.com --port=5432 --username=postgres -d north_america < north_america.dump
cd ../../bash

cd ../data/south-america
psql --host=geomagnetic-storm-model.cqicqdey3ckh.us-east-2.rds.amazonaws.com --port=5432 --username=postgres -d south_america < south_america.dump
cd ../../bash


#cd ../data/central-america
# psql --host=geomagnetic-storm-model.cqicqdey3ckh.us-east-2.rds.amazonaws.com --port=5432 --username=postgres -d central_america < central_america.dump
#cd ../../bash


cd ../data/australia-oceania
psql --host=geomagnetic-storm-model.cqicqdey3ckh.us-east-2.rds.amazonaws.com --port=5432 --username=postgres -d australia_oceania < australia_oceania.dump
cd ../../bash

cd ../data/russia
psql --host=geomagnetic-storm-model.cqicqdey3ckh.us-east-2.rds.amazonaws.com --port=5432 --username=postgres -d russia < russia.dump
cd ../../bash


cd ../data/asia
psql --host=geomagnetic-storm-model.cqicqdey3ckh.us-east-2.rds.amazonaws.com --port=5432 --username=postgres -d asia < asia.dump
cd ../../bash


cd ../data/europe
psql --host=geomagnetic-storm-model.cqicqdey3ckh.us-east-2.rds.amazonaws.com --port=5432 --username=postgres -d europe < europe.dump
cd ../../bash


cd ../data/africa
psql --host=geomagnetic-storm-model.cqicqdey3ckh.us-east-2.rds.amazonaws.com --port=5432 --username=postgres -d africa < africa.dump
cd ../../bash




