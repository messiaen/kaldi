#!/bin/bash

N=$1

VOCAB_DIR="nbest-vocab-$N"
VOCAB_SLF_DIR="nbest-vocab-slfs-$N"

mkdir $VOCAB_DIR $VOCAB_SLF_DIR


for lat in ./lat.*.gz; do 
	gunzip -c $lat | \
		lattice-scale --acoustic-scale=0.08333 --lm-scale=1.0 ark:- ark:- | \
		lattice-align-words $LANG_DIR/phones/word_boundary.int /home/eigenmoose/workspace/kaldi-trunk/egs/librispeech/s5/exp/nnet2_online/nnet_ms_a_online/final.mdl ark:- ark:- | \
		lattice-to-nbest --n=$N ark:- ark:- | \
		nbest-to-lattice ark:- ark:- | \
		lattice-arc-post /home/eigenmoose/workspace/kaldi-trunk/egs/librispeech/s5/exp/nnet2_online/nnet_ms_a_online/final.mdl ark:- - | \
		int2sym.pl -f 5 $LANG_DIR/words.txt | gzip -c - > $VOCAB_DIR/$(basename $lat)
done


python vocab2cnet.py ref.stm $VOCAB_DIR $VOCAB_SLF_DIR
