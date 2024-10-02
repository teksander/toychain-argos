# [PATHS]
export HOMEFOLDER="$HOME"
export MAINFOLDER="$HOMEFOLDER/toychain-argos"
export ARGOSFOLDER="$MAINFOLDER/argos-python"
export TOYCHFOLDER="$MAINFOLDER/toychain"
export EXPERIMENTFOLDER="$MAINFOLDER/MarketForaging"
# [[ ":$PATH:" != *":$MAINFOLDER/scripts:"* ]] && export PATH=$PATH:$MAINFOLDER/scripts

# [FILES]
export ARGOSNAME="market-foraging"
export SCNAME="noepochs"
export CONTRACTNAME="MarketForaging"

export ARGOSFILE="${EXPERIMENTFOLDER}/experiments/${ARGOSNAME}.argos"
export ARGOSTEMPLATE="${EXPERIMENTFOLDER}/experiments/${ARGOSNAME}.x.argos"
export SCFILE="${EXPERIMENTFOLDER}/scs/${SCNAME}.py" 

# [ARGOS]
export NUM1=20
export CON1="${EXPERIMENTFOLDER}/controllers/main_collab_noepochs.py"

export NUM2=0
export CON2="${EXPERIMENTFOLDER}/controllers/main_greedy.py"

export RABRANGE="2"
export WHEELNOISE="0"
export TPS=10
export DENSITY="1"

export NUMROBOTS=$(echo $NUM1+$NUM2 | bc)
export ARENADIM=$(echo "scale=3 ; sqrt($NUMROBOTS/$DENSITY)" | bc)
export ARENADIMH=$(echo "scale=3 ; $ARENADIM/2" | bc)
export STARTDIM=$(echo "scale=3 ; $ARENADIM/5" | bc)

# [GETH]
export BLOCKPERIOD=2

# [SC]
export MAXWORKERS=15
export STARTWORKERS=3
export LIMITASSIGN=2

export DEMAND_A=0
export DEMAND_B=1000
export REGENRATE=20
export FUELCOST=100
export QUOTA_temp=$(echo " scale=4 ; (75/$REGENRATE*$BLOCKPERIOD+0.05)/1" | bc)
export QUOTA=$(echo "$QUOTA_temp*10/1" | bc)
export QUOTA=200
export EPSILON=15
export WINSIZE=5

# [OTHER]
export SEED=1500
export TIMELIMIT=100
export LENGTH=5000
export SLEEPTIME=5
export REPS=5
export NOTES="Variation of utility of the resource between 100 and 400"




