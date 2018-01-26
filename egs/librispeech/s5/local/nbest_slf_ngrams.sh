#!/bin/bash


N=$1


echo "Computing $N-best ngrams from $N-best slfs"


SLF_DIR=./nbest-slfs-$N
SLF_NGRAM_DIR=./nbest-slf-ngrams-$N


mkdir $SLF_NGRAM_DIR

for lat in $SLF_DIR/*.lat.gz; do
	fn=$(basename $lat)
	outfn=$SLF_NGRAM_DIR/${fn%.*.gz}.ngrams.gz
	#echo $outfn
	zcat $lat | \
		lattice-tool -in-lattice - -read-htk -write-htk -out-lattice - | \
		lattice-tool -in-lattice - -read-htk -order 3 -ngrams-time-tolerance 0.25 -write-ngrams - | \
		grep -Ev '(<s>|<\/s>)' | gzip -c - > $outfn
done
