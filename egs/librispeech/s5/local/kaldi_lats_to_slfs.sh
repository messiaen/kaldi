

KALDI_LAT_DIR=$1
OUTDIR=$2
SCRIPTDIR=$(dirname $(readlink -f $0))

for LATFILE in $KALDI_LAT_DIR/lat.*.gz; do 
	$SCRIPTDIR/to_slfs.sh $LATFILE $OUTDIR
done


for LATFILE in $OUTDIR/*.lat.gz; do
	gunzip $LATFILE
done
