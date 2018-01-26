#!/bin/bash


SLF_DIR=./slfs
SLF_NGRAM_DIR=./slf-ngrams


mkdir $SLF_NGRAM_DIR

for lat in $SLF_DIR/*.lat; do
	fn=$(basename $lat)
	outfn=$SLF_NGRAM_DIR/${fn%.*}.ngrams.gz
	echo $outfn
	cat $lat | \
		lattice-tool -in-lattice - -read-htk -write-htk -out-lattice - | \
		lattice-tool -in-lattice - -read-htk -order 3 -ngrams-time-tolerance 0.25 -write-ngrams - | \
		grep -Ev '(<s>|<\/s>)' | gzip -c - > $outfn
done
