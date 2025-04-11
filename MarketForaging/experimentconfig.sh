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
export NUMA=15
export NUMB=0
export NUMC=0
export NUMD=0
export NUMAB=$(echo $NUMA+$NUMB| bc)
export NUMABC=$(echo $NUMA+$NUMB+$NUMC| bc)

export CON1="${EXPERIMENTFOLDER}/controllers/main_individ.py"

export ORACLE="False"

export RABRANGE_A="0.50"
# export RABRANGE_B="0.40"
# export RABRANGE_C="0.40"
# export RABRANGE_D="0.40"

export WHEELNOISE="0"
export TPS=10
export DENSITY="0.8"

export NUMROBOTS=$(echo $NUMA+$NUMB+$NUMC+$NUMD | bc)
export ARENADIM=$(echo "scale=3 ; sqrt($NUMROBOTS/$DENSITY)" | bc)
export ARENADIMH=$(echo "scale=3 ; $ARENADIM/2" | bc)
export STARTDIM=$(echo "scale=3 ; $ARENADIM/5" | bc)
export FOCALLGT=$(echo "scale=3 ; -2 * $ARENADIM + 16" | bc)


# [GETH]
export BLOCKPERIOD=2

# [SC]
export MAXWORKERS=15
export STARTWORKERS=1
export LIMITASSIGN=2

export DEMAND_A=0
export DEMAND_B=1
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




