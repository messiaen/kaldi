#!/bin/bash

N=$1

SLF_DIR="nbest-slfs-$N"
SLF_CONF_DIR="nbest-slfs-with-conf-$N"

mkdir $SLF_DIR $SLF_CONF_DIR


for lat in ./lat.*.gz; do 
	gunzip -c $lat | \
		lattice-scale --acoustic-scale=0.08333 --lm-scale=1.0 ark:- ark:- | \
		lattice-align-words $LANG_DIR/phones/word_boundary.int /home/eigenmoose/workspace/kaldi-trunk/egs/librispeech/s5/exp/nnet2_online/nnet_ms_a_online/final.mdl ark:- ark:- | \
		lattice-to-nbest --n=$N ark:- ark:- | \
		nbest-to-lattice ark:- ark,t:- | \
		int2sym.pl -f 3 $LANG_DIR/words.txt | \
		convert_slf.pl - $SLF_DIR/
done

for lat in $SLF_DIR/*; do 
	fn=$(basename $lat)
	zcat $lat | ./add_confidence.sh > $SLF_CONF_DIR/${fn%.*}
done


for lat in $SLF_CONF_DIR/*.lat; do
	readlink -f $lat >> $SLF_CONF_DIR/cnet.lst
done
