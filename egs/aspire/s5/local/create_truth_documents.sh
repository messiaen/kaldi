#!/bin/bash

truth=${1}
docs=${2}

mkdir -p ${docs}

doc_id_fn=$(pwd)/doc_ids

cut -d '-' -f 1,2 ${truth} | sort -u > ${doc_id_fn}

for id in $(cat ${doc_id_fn}); do
	doc_fn=${docs}/${id}
	grep ${id} ${truth} > ${doc_fn}
done

rm $doc_id_fn
