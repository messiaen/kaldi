#!/usr/bin/env python

import sys
import os
import re
import subprocess
import gzip
import numpy as np
from collections import defaultdict


MIN_DIFF = 1e-32


utt_pat = re.compile(r'(.*)-(\d+)$')


def collect_scores(costs_f):
    scores = defaultdict(dict)

    for line in costs_f:
        if len(line.strip()) < 1:
            continue
        utt, cost = line.strip().split()[:2]
        m = utt_pat.match(utt.decode('utf-8'))
        if m:
            utt_name = m.group(1)
            hyp_n = m.group(2)
            scores[utt_name][hyp_n] = float(cost)

    return scores


def key_tuple(x):
    m = utt_pat.match(x[0])
    return m.group(1), float(m.group(2))


def compute_conf(ac_f, lm_f, conf_f):
    ac_scores = collect_scores(ac_f)
    lm_scores = collect_scores(lm_f)

    combined_scores = defaultdict(dict)

    for utt_name, hyps in ac_scores.items():
        for hyp_n, cost in hyps.items():
            combined_scores[utt_name][hyp_n] = -lm_scores[utt_name][hyp_n] + -cost

    aggs = {}
    for utt_name, hyps in combined_scores.items():
        values = list(hyps.values())
        S = np.sum(values)
        min_s = np.min(values)
        max_s = np.max(values)

        aggs[utt_name] = (S, min_s, max_s)

    final_scores = []

    for utt_name, hyps in combined_scores.items():
        for hyp_n, cost in hyps.items():
            prob = cost / aggs[utt_name][0]
            conf = (cost / max(MIN_DIFF, (aggs[utt_name][2] - aggs[utt_name][1]))) * 100

            final_scores.append((
                '{}-{}'.format(utt_name, hyp_n),
                ac_scores[utt_name][hyp_n],
                lm_scores[utt_name][hyp_n],
                combined_scores[utt_name][hyp_n],
                conf,
                prob))

    for score in sorted(final_scores, key=key_tuple):
        l = '{} {} {} {} {} {}\n'.format(*score)
        conf_f.write(l.encode())


def write_nbest_list(lat_fn, ac_fn, lm_fn, ali_fn, tra_fn, n=100):
    gunzip_p = subprocess.Popen(('gunzip', '-c', lat_fn), stdout=subprocess.PIPE)
    lattice_scale_p = subprocess.Popen(('lattice-scale',
                                        '--acoustic-scale=0.08333',
                                        '--lm-scale=1.0',
                                        'ark:-',
                                        'ark:-'),
                                       stdin=gunzip_p.stdout,
                                       stdout=subprocess.PIPE)
    lattice_nbest_p = subprocess.Popen(('lattice-to-nbest',
                                        '--n={}'.format(n),
                                        'ark:-',
                                        'ark:-'),
                                       stdin=lattice_scale_p.stdout,
                                       stdout=subprocess.PIPE)
    nbest_to_linear_p = subprocess.Popen(('nbest-to-linear',
                                          'ark:-',
                                          'ark,t:|gzip -c - > {}'.format(ali_fn),
                                          'ark,t:| int2sym.pl -f 2- $LANG_DIR/words.txt | gzip -c - > {}'.format(tra_fn),
                                          'ark,t:| gzip -c - > {}'.format(lm_fn),
                                          'ark,t:| gzip -c - > {}'.format(ac_fn)),
                                         stdin=lattice_nbest_p.stdout)

    nbest_to_linear_p.wait()


def write_vocabs(tra_fn, vocabs_dir):
    with gzip.open(tra_fn, 'r') as tra_f:
        for line in tra_f:
            if len(line.strip()) < 1:
                continue
            utt, *words = line.strip().split()
            utt_id = utt_pat.match(utt.decode()).group(1)
            vocab_fn = os.path.join(vocabs_dir, utt_id.vocab)
            with open(vocab_fn, 'w') as vocab_f:
                vocab_f.write('\n'.join(words))


def main():
    lat_fn = sys.argv[1]
    n = sys.argv[2]
    lat_n = os.path.basename(lat_fn).split('.')[1]

    ac_fn = 'accost.{}.gz'.format(lat_n)
    lm_fn = 'lmcost.{}.gz'.format(lat_n)
    ali_fn = 'ali.{}.gz'.format(lat_n)
    tra_fn = 'tra.{}.gz'.format(lat_n)
    conf_fn = 'cost.{}.gz'.format(lat_n)

    write_nbest_list(lat_fn, ac_fn, lm_fn, ali_fn, tra_fn, n=n)

    with gzip.open(ac_fn, 'r') as ac_f, gzip.open(lm_fn, 'r') as lm_f, gzip.open(conf_fn, 'w') as conf_f:
        compute_conf(ac_f, lm_f, conf_f)


if __name__ == '__main__':
    main()
