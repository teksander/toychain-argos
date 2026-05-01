# [PATHS]
export HOMEFOLDER="$HOME"
export MAINFOLDER="$HOMEFOLDER/toychain-argos"
export ARGOSFOLDER="$MAINFOLDER/argos-python"
export TOYCHFOLDER="$MAINFOLDER/toychain"
export EXPERIMENTFOLDER="$MAINFOLDER/HelloNeighbor"

# [FILES]
export ARGOSNAME="greeter"
export ARGOSFILE="${EXPERIMENTFOLDER}/experiments/${ARGOSNAME}.argos"
export ARGOSTEMPLATE="${EXPERIMENTFOLDER}/experiments/${ARGOSNAME}.x.argos"

# export CONTRACTADDRESS="${EXPERIMENTFOLDER}/scs/contractAddress.txt"
# export CONTRACTNAME="MarketForaging"
export SCNAME="greeter"
export SCFILE="${EXPERIMENTFOLDER}/scs/${SCNAME}.py" 
# export SCTEMPLATE="${EXPERIMENTFOLDER}/scs/${SCNAME}.x.py" 

export GENESISFILE="${DOCKERFOLDER}/geth/files/$GENESISNAME.json"

# [ARGOS]
export NUM1=20
export CON1="${EXPERIMENTFOLDER}/controllers/main.py"

export NUM2=0
export CON2="${EXPERIMENTFOLDER}/controllers/main_greedy.py"

export RABRANGE="0.5"
export WHEELNOISE="0"
export TPS=10
export DENSITY="0.5"

export NUMROBOTS=$(echo $NUM1+$NUM2 | bc)
export ARENADIM=$(echo "scale=3 ; sqrt($NUMROBOTS/$DENSITY)" | bc)
export ARENADIMH=$(echo "scale=3 ; $ARENADIM/2" | bc)
export STARTDIM=$(echo "scale=3 ; $ARENADIM/5" | bc)

# [TOYCHAIN]
export BLOCKPERIOD=2
export EXPLORER="True"
export EXPLORER_PATH="$TOYCHFOLDER/src/plugins/toychain-explorer/"
export EXPLORER_HOST="localhost"
export EXPLORER_PORT="8765"

# [SC]

# [OTHER]
export SEED=1500
export TIMELIMIT=500
export LENGTH=1000
export SLEEPTIME=5
export REPS=5
export NOTES="Variation of utility of the resource between 100 and 400"




