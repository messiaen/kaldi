from elasticsearch import Elasticsearch
from collections import defaultdict
import numpy as np
import gzip
import sys


fn = sys.argv[1]


words = defaultdict(lambda: defaultdict(list))


with gzip.open(fn, 'r') as f:
    for line in f:
        if len(line.strip()) < 1:
            continue
        fields = line.strip().split()
        utt_id = fields[0]
        word = fields[4]
        post = float(fields[3])

        words[utt_id][word].append(post)

es = Elasticsearch()
for utt_id, word_d in words.items():
    vocab = []
    for word, posts in word_d.items():
        max_post = np.max(posts)
        min_post = np.min(posts)
        mean_post = np.mean(posts)
        S_posts = np.sum(posts)

        vocab.append({'word': word.decode(),
                      'max_post': max_post,
                      'min_post': min_post,
                      'mean_post': mean_post,
                      'sum_posts': S_posts,
                      'utt_freq': 1.0
                     })

    res = es.index(index='test_docs_1', doc_type='transcript', id=utt_id, body={'vocab': vocab})
    print(res)


