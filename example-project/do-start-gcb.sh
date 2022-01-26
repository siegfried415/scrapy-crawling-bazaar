StopAllDaemons()
{
	echo "Stop all gcb daemons..."
	killall -9 gcb
}

StopAllDaemons
sleep 5 

gcb="/home/wyong/go-crawling-bazaar/bin/gcb"
StartDaemon()
{
	echo "start $2 daemon with repo $1 and log $1/daemon.log ..."
	$gcb --repodir $1 --log-level debug --role $2 daemon > "$1/daemon.log" 2>&1 
	sleep 5 
}

StartDaemon "./gcb/node_0"  "Leader" &
StartDaemon "./gcb/node_1"  "Follower" &
StartDaemon "./gcb/node_2"  "Follower" &

sleep 5 
for i in 0 1 2 3 4 5 6 7 8 9 
do
	StartDaemon "./gcb/node_miner_$i"  "Miner" &
done 

sleep 5 
StartDaemon "./gcb/node_c" "Client" &
wait 
