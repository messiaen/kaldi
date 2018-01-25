import sys
import re
import os
import gzip
import numpy as np
from collections import defaultdict


utt_pat = re.compile(r'(.*)-(\d+)$')


ac_fn = sys.argv[1]
lm_fn = sys.argv[2]


def collect_scores(costs_f):
    scores = defaultdict(dict)

    for line in f:
        if len(line.strip()) < 1:
            continue
        utt, cost = line.strip().split()[:2]
        m = utt_pat.match(utt.decode('utf-8'))
        if m:
            utt_name = m.group(1)
            hyp_n = m.group(2)
            scores[utt_name][hyp_n] = float(cost)

    return scores


with gzip.open(ac_fn, 'r') as f:
    ac_scores = collect_scores(f)


with gzip.open(lm_fn, 'r') as f:
    lm_scores = collect_scores(f)


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
        conf = (cost / (aggs[utt_name][2] - aggs[utt_name][1])) * 100

        final_scores.append((
            '{}-{}'.format(utt_name, hyp_n),
            ac_scores[utt_name][hyp_n],
            lm_scores[utt_name][hyp_n],
            combined_scores[utt_name][hyp_n],
            conf,
            prob))


def key_tuple(x):
    m = utt_pat.match(x)
    return m.group(1), float(m.group(2))


for score in sorted(final_scores, key=lambda x: key_tuple(x[0])):
    print('{} {} {} {} {} {}'.format(*score))

