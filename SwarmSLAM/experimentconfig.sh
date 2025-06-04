# [PATHS]
export HOMEFOLDER="$HOME"
export MAINFOLDER="$HOMEFOLDER/toychain-argos"
export ARGOSFOLDER="$MAINFOLDER/argos-python"
export TOYCHFOLDER="$MAINFOLDER/toychain"
export EXPERIMENTFOLDER="$MAINFOLDER/SwarmSLAM"

# [FILES]
export ARGOSNAME="greeter"
export ARGOSFILE="${EXPERIMENTFOLDER}/experiments/${ARGOSNAME}.argos"
export ARGOSTEMPLATE="${EXPERIMENTFOLDER}/experiments/${ARGOSNAME}.x.argos"

export SCNAME="greeter"
export SCFILE="${EXPERIMENTFOLDER}/scs/${SCNAME}.py" 

# [ARGOS]
export NUM1=15
export CON1="${EXPERIMENTFOLDER}/controllers/main.py"

export RABRANGE="0.6"
export WHEELNOISE="0"
export TPS=10
# export DENSITY="1"

export NUMROBOTS=$(echo $NUM1 | bc)
# export ARENADIM=$(echo "scale=3 ; sqrt($NUMROBOTS/$DENSITY)" | bc)
# export ARENADIMH=$(echo "scale=3 ; $ARENADIM/2" | bc)
# export STARTDIM=$(echo "scale=3 ; $ARENADIM/5" | bc)

export NUMBOX=2
export NUMCYL=3

export DIAMCYL=0.4
export SIDEBOX=0.9

export ARENADIM=6
export ARENADIMH=3
export STARTDIM=$(echo "scale=3 ; $ARENADIM*2/5" | bc)
export OBJRANGE=1.5

# [SC]
export MAXWORKERS=15

# [OTHER]
export SEED=1500
export TIMELIMIT=50000
export LENGTH=5000
export SLEEPTIME=5
export REPS=5
export NOTES="e.g. description of the experiment"




