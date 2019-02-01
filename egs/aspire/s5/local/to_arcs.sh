#!/bin/bash

. path.sh
. cmd.sh

export LANG_DIR=`pwd`/data/lang
export MODEL_DIR=`pwd`/exp/tdnn_7b_chain_online
export PYTHONPATH=/export/b05/gclar/opt/lib/python2.7/site-packages
export LD_LIBRARY_PATH=/export/b05/gclar/opt/lib:$LD_LIBRARY_PATH

python local/to_arcs.py $@
