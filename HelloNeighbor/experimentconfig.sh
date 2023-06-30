# [PATHS]
export HOMEFOLDER=$HOME
export MAINFOLDER="$HOMEFOLDER/toychain-argos"
export DOCKERFOLDER="$MAINFOLDER/toychain"
export ARGOSFOLDER="$MAINFOLDER/argos-python"
export EXPERIMENTFOLDER="$MAINFOLDER/HelloNeighbor"
# export BLOCKCHAINPATH="$HOMEFOLDER/eth_data_para/data"

# [FILES]
export ARGOSNAME="greeter"
export GENESISNAME="genesis_poa"

export ARGOSFILE="${EXPERIMENTFOLDER}/experiments/${ARGOSNAME}.argos"
export ARGOSTEMPLATE="${EXPERIMENTFOLDER}/experiments/${ARGOSNAME}.argosx"

# [ARGOS]
export NUM1=20
export CON1="${EXPERIMENTFOLDER}/controllers/main.py"

export TPS=20
export DENSITY="2"

export NUMROBOTS=$(echo $NUM1 | bc)
export ARENADIM=$(echo "scale=3 ; sqrt($NUMROBOTS/$DENSITY)" | bc)
export ARENADIMH=$(echo "scale=3 ; $ARENADIM/2" | bc)
export STARTDIM=$(echo "scale=3 ; $ARENADIM/5" | bc)

# [GETH]
export BLOCKPERIOD=2

# [OTHER]
export SEED=0
export TIMELIMIT=100
export SLEEPTIME=5
export REPS=4
export NOTES=""




