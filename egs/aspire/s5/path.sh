export KALDI_ROOT=`pwd`/../../..
export PATH=$PWD/utils/:$KALDI_ROOT/tools/openfst/bin:$PWD:$PATH
[ ! -f $KALDI_ROOT/tools/config/common_path.sh ] && echo >&2 "The standard file $KALDI_ROOT/tools/config/common_path.sh is not present -> Exit!" && exit 1
. $KALDI_ROOT/tools/config/common_path.sh
export PATH=$KALDI_ROOT/tools/sctk/bin:$PATH
export LC_ALL=C

#export LANG_DIR=`pwd`/data/lang
#export MODEL_DIR=`pwd`/exp/tdnn_7b_chain_online
#export PYTHONPATH=/export/b05/gclar/opt/lib/python2.7/site-packages
#export LD_LIBRARY_PATH=/export/b05/gclar/opt/lib:$LD_LIBRARY_PATH
