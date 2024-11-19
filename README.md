# ARGoS-Blockchain Interface in Python

AUTHOR: 

Alexandre Pacheco  <alexandre.melo.pacheco@gmail.com>

CREDITS:

Ken Hasselmann for argos-python wrapper <https://github.com/KenN7/argos-python>

Ulysse Denis for implementing a mockup blockchain in python <https://github.com/uldenis/PROJH402>

DATE: 20/02/2023


# Installation guide
This guide assumes a previously clean installation of Ubuntu20.04 or Ubuntu22.04

## ARGoS

Step 1: Download and compile ARGoS version 59
(More information at https://github.com/ilpincy/argos3)
```
sudo apt install git build-essential cmake g++ libfreeimage-dev libfreeimageplus-dev freeglut3-dev \
libxi-dev libxmu-dev liblua5.3-dev lua5.3 doxygen graphviz graphviz-dev asciidoc
```
On Ubuntu 20.04 do
```
sudo apt install qt5-default
```
On Ubuntu 22.04 do
```
sudo apt install qtbase5-dev qt5-qmake
```
Then, install argos3 system-wide
```
git clone https://github.com/ilpincy/argos3.git

cd argos3/
mkdir build
cd build
cmake ../src
make -j4
make doc
sudo make install
sudo ldconfig
```

Step 2: Download and compile E-puck plugin
(More information at https://github.com/demiurge-project/argos3-epuck)
```
git clone https://github.com/demiurge-project/argos3-epuck.git

cd argos3-epuck/
mkdir build
cd build
cmake ../src
make
sudo make install
sudo ldconfig
```

## Put it all together

Step 1: Clone the repo

```
git clone --recurse-submodules https://github.com/teksander/toychain-argos.git
```

Step 2: Compile ARGoS-Python and install dependencies

```
sudo apt-get install g++ cmake git libboost-python-dev

cd argos-python
git fetch
git checkout temp
mkdir build
cd build
cmake ..
make
```

Step 3: Configuration and Run

Edit ```experimentconfig.sh``` file to match your paths\
Install some python packages used in the robot controllers
```
sudo apt install python3-pip
pip install aenum psutil hexbytes 
```
Then run an experiment

```
cd toychain-argos/HelloNeighbor
./starter -s
```
