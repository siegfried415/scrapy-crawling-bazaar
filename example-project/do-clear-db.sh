#find . -name "chain.db" -exec rm -fr {} \; -print 
#find . -type d -name "data" -exec rm -fr {} \; -print 

for i in 0 1 2 
do
	rm -fr ./gcb/node_$i/chain.db
	rm -fr ./gcb/node_$i/data/*
done 

for i in 0 1 2 3 4 5 6 7 8 9 
do
	rm -fr ./gcb/node_miner_$i/chain.db
	rm -fr ./gcb/node_miner_$i/data/*
done 
