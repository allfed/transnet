cd ../data/north-america
#psql -U postgres -p 64803 -d north_america -h pn002 < north_america.dump
cd ../../bash
cd ../data/south-america
#psql -U postgres -p 64803 -d south_america -h pn002 < south_america.dump
cd ../../bash
cd ../data/central-america
# psql -U postgres -p 64803 -d central_america -h pn002 < central_america.dump
cd ../../bash
cd ../data/australia-oceania
#psql -U postgres -p 64803 -d australia_oceania -h pn002 < australia_oceania.dump
cd ../../bash
cd ../data/russia
#psql -U postgres -p 64803 -d russia -h pn002 < russia.dump
cd ../../bash
cd ../data/asia
psql -U postgres -p 64803 -d asia -h pn002 < asia.dump
cd ../../bash
cd ../data/europe
# psql -U postgres -p 64803 -d europe -h pn002 < europe.dump
cd ../../bash
cd ../data/africa
psql -U postgres -p 64803 -d africa -h pn002 < africa.dump
cd ../../bash

