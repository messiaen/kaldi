#!/bin/bash

KALDI_HOME=/home/eigenmoose/workspace/kaldi-trunk

LATTCP=$KALDI_HOME/src/latbin/lattice-copy

LATFILE=$1

OUTPUT_DIR=$2

INT2SYM=$KALDI_HOME/egs/librispeech/s5/utils/int2sym.pl

WORDS=/home/eigenmoose/workspace/kaldi-trunk/egs/librispeech/s5/exp/nnet2_online/nnet_ms_a_online/graph_test/words.txt

CONV_SLF=$KALDI_HOME/egs/librispeech/s5/utils/convert_slf.pl

mkdir -p $OUTPUT_DIR
$LATTCP "ark:zcat $LATFILE |" ark,t:- | $INT2SYM -f 3 $WORDS > /tmp/$(basename $LATFILE)
$CONV_SLF /tmp/$(basename $LATFILE) $OUTPUT_DIR
rm -f /tmp/$(basename $LATFILE)

