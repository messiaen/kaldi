#!/usr/bin/env python

import sys
import os
import re
import subprocess
import gzip
import numpy as np
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import tempfile
import io
from functools import partial


MIN_DIFF = 1e-32


utt_pat = re.compile(r'(.*)-(\d+)$')

def compute_nbest_list(fn, n=10):
    lat_n = os.path.basename(fn).split('.')[1]
    outdir = os.path.dirname(fn)
    ac_fn = os.path.join(outdir, 'accost.{}.gz'.format(lat_n))
    lm_fn = os.path.join(outdir, 'lmcost.{}.gz'.format(lat_n))
    tra_fn = os.path.join(outdir, 'tra.{}.gz'.format(lat_n))

    write_nbest_list(fn, ac_fn, lm_fn, tra_fn, n=n)

    with gzip.open(ac_fn, 'rt', encoding='utf-8') as ac_f, \
            gzip.open(lm_fn, 'rt', encoding='utf-8') as lm_f, \
            gzip.open(tra_fn, 'rt', encoding='utf-8') as tra_f:
        return compute_conf(ac_f, lm_f, tra_f)



def collect_scores(costs_f):
    scores = defaultdict(dict)

    for line in costs_f:
        if len(line.strip()) < 1:
            continue
        utt, cost = line.strip().split()[:2]
        m = utt_pat.match(utt)
        if m:
            utt_name = m.group(1)
            hyp_n = m.group(2)
            scores[utt_name][hyp_n] = float(cost)

    return scores


def key_tuple(x):
    m = utt_pat.match(x[0])
    return m.group(1), float(m.group(2))


def read_tra_file(tra_f):
    trans = defaultdict(dict)
    for line in tra_f:
        if len(line.strip()) < 1:
            continue
        fields = line.strip().split()
        utt_id_hyp = fields[0]
        if len(fields) < 2:
            t = ''
        else:
            t = ' '.join(fields[1:])
        hyp = utt_id_hyp.split('-')[-1]
        utt_id = '-'.join(utt_id_hyp.split('-')[:-1])
        trans[utt_id][hyp] = t

    return trans


def compute_conf(ac_f, lm_f, tra_f):
    ac_scores = collect_scores(ac_f)
    lm_scores = collect_scores(lm_f)
    trans = read_tra_file(tra_f)

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
                utt_name,
                hyp_n,
                trans[utt_name][hyp_n],
                ac_scores[utt_name][hyp_n],
                lm_scores[utt_name][hyp_n],
                combined_scores[utt_name][hyp_n],
                conf,
                prob))

    return final_scores


def write_nbest_list(lat_fn, ac_fn, lm_fn, tra_fn, n=100):
    lang_dir = os.environ['LANG_DIR']
    gunzip_p = subprocess.Popen(('gunzip', '-c', lat_fn), stdout=subprocess.PIPE)
    lattice_nbest_p = subprocess.Popen(('lattice-to-nbest',
                                        '--n={}'.format(n),
                                        'ark:-',
                                        'ark:-'),
                                       stdin=gunzip_p.stdout,
                                       stdout=subprocess.PIPE)
    nbest_to_linear_p = subprocess.Popen(('nbest-to-linear',
                                          'ark:-',
                                          'ark:/dev/null',
                                          'ark,t:| int2sym.pl -f 2- {}/words.txt | gzip -c - > {}'.format(lang_dir, tra_fn),
                                          'ark,t:| gzip -c - > {}'.format(lm_fn),
                                          'ark,t:| gzip -c - > {}'.format(ac_fn)),
                                         stdin=lattice_nbest_p.stdout)

    nbest_to_linear_p.wait()


def file_pairs(indir, inprefix, outdir, outprefix):
    for fn in os.listdir(indir):
        if not re.compile(r'{}\.[0-9]+\.gz'.format(inprefix)).match(fn):
            continue
        lat_fn = os.path.join(indir, fn)
        lat_n = fn.split('.')[1]
        out_fn = os.path.join(outdir, '{}.{}.gz'.format(outprefix, lat_n))
        yield lat_fn, out_fn


def file_lst_pairs(fns, outdir, outprefix):
    for fn in fns:
        lat_n = os.path.basename(fn).split('.')[1]
        out_fn = os.path.join(outdir, '{}.{}.gz'.format(outprefix, lat_n))
        yield fn, out_fn


def write_aligned_lats(indir, outdir):
    with ThreadPoolExecutor(max_workers=3) as executor:
        return executor.map(write_aligned_lat, *zip(*file_pairs(indir, 'lat', outdir, 'aligned')))


def write_aligned_lat(lat_fn, out_fn):
    model_dir = os.environ['MODEL_DIR']
    lang_dir = os.environ['LANG_DIR']
    gunzip_p = subprocess.Popen(('gunzip', '-c', lat_fn), stdout=subprocess.PIPE)
    lattice_scale_p = subprocess.Popen(('lattice-scale',
                                        '--acoustic-scale=0.08333',
                                        '--lm-scale=1.0',
                                        'ark:-',
                                        'ark:-'),
                                       stdin=gunzip_p.stdout,
                                       stdout=subprocess.PIPE)
    align_lattice_p = subprocess.Popen(('lattice-align-words',
                                        '{}/phones/word_boundary.int'.format(lang_dir),
                                        '{}/final.mdl'.format(model_dir),
                                        'ark:-',
                                        'ark:| gzip -c - > {}'.format(out_fn)),
                                       stdin=lattice_scale_p.stdout)

    return_code = align_lattice_p.wait()
    if return_code != 0:
        raise Exception('Error writing aligned lattices: cmd returned {}'.format(return_code))
    return out_fn


def write_slfs(in_fns, outdir):
    with ThreadPoolExecutor(max_workers=3) as executor:
        list(executor.map(write_lat_to_slfs, in_fns, (outdir for _ in range(len(in_fns)))))
    yield from map(lambda fn: os.path.join(outdir, fn), filter(lambda fn: re.compile(r'.*.lat.gz').match(fn), os.listdir(outdir)))


def write_lat_to_slfs(aligned_lat_fn, outdir):
    model_dir = os.environ['MODEL_DIR']
    lang_dir = os.environ['LANG_DIR']
    gunzip_p = subprocess.Popen(('gunzip', '-c', aligned_lat_fn), stdout=subprocess.PIPE)
    copy_p = subprocess.Popen(('lattice-copy', 'ark:-', 'ark,t:-'),
                              stdin=gunzip_p.stdout,
                              stdout=subprocess.PIPE)
    int2sym_p = subprocess.Popen(('int2sym.pl', '-f', '3', '{}/words.txt'.format(lang_dir)),
                                  stdin=copy_p.stdout,
                                  stdout=subprocess.PIPE)
    convert_slf_p = subprocess.Popen(('convert_slf.pl', '-', outdir),
                                     stdin=int2sym_p.stdout,
                                     stdout=subprocess.PIPE)
    code = convert_slf_p.wait()
    if code != 0:
        raise Exception('Error writing slfs: cmd returned {}'.format(code))


def one_best_ctms(fns):
    ctms = []
    with ThreadPoolExecutor(max_workers=3) as executor:
        for ctm_lst in executor.map(one_best_ctm, fns):
            ctms.extend(ctm_lst)
    return ctms


def one_best_ctm(aligned_lat_fn):
    model_dir = os.environ['MODEL_DIR']
    lang_dir = os.environ['LANG_DIR']
    gunzip_p = subprocess.Popen(('gunzip', '-c', aligned_lat_fn), stdout=subprocess.PIPE)
    to_ctm_p = subprocess.Popen(('lattice-to-ctm-conf', 'ark:-', '-'),
                                stdin=gunzip_p.stdout,
                                stdout=subprocess.PIPE)
    int2sym_p = subprocess.Popen(('int2sym.pl', '-f', '5', '{}/words.txt'.format(lang_dir)),
                                  stdin=to_ctm_p.stdout,
                                  stdout=subprocess.PIPE)
    out_ctm, _ = int2sym_p.communicate()
    code = int2sym_p.wait()
    if code != 0:
        raise Exception('Failed to convert to ctms')
    ctms = convert_ctm_file(out_ctm.decode('utf-8').split('\n'))
    return ctms


def convert_ctm_file(ctm_f):
    ctms = []
    last_id = None
    for row in map(str.split, filter(lambda l: len(l.strip()) > 0, ctm_f)):
        if last_id == None or last_id != row[0]:
            last_id = row[0]
            ctms.append([])
        ctms[-1].append(row)
    return ctms


def compute_ngrams(fns, n=3):
    ngrams_lst = []
    with ThreadPoolExecutor(max_workers=3) as executor:
        for ngrams in executor.map(partial(compute_slf_ngrams, n=3), fns):
            ngrams_lst.append(ngrams)
    return ngrams_lst


def compute_slf_ngrams(fn, n=3):
    utt_id = os.path.basename(fn).split('.')[0]
    gunzip_p = subprocess.Popen(('gunzip', '-c', fn), stdout=subprocess.PIPE)
    tool_p1 = subprocess.Popen(('lattice-tool',
                                '-in-lattice',
                                '-',
                                '-read-htk',
                                '-write-htk',
                                '-out-lattice',
                                '-'),
                               stdin=gunzip_p.stdout,
                               stdout=subprocess.PIPE)
    tool_p2 = subprocess.Popen(('lattice-tool',
                                '-in-lattice',
                                '-',
                                '-read-htk',
                                '-order',
                                str(n),
                                '-ngrams-time-tolerance',
                                '0.25',
                                '-write-ngrams',
                                '-'),
                               stdin=tool_p1.stdout,
                               stdout=subprocess.PIPE)

    out_ngrams, _ = tool_p2.communicate()
    code = tool_p2.wait()
    if code != 0:
        raise Exception('Failed to compute ngrams')

    ngrams = convert_ngram_file(utt_id, out_ngrams.decode('utf-8').split('\n'))
    return ngrams


def convert_ngram_file(utt_id, ngram_f):
    ngrams = []
    for line in ngram_f:
        if len(line.strip()) < 1:
            continue
        if '<s>' in line or '</s>' in line:
            continue
        fields = line.split()
        ngrams.append((utt_id, tuple(fields[:-1]), float(fields[-1])))
    return ngrams


def compute_vocab(fns, min_post=0.0001):
    vocabs = []
    with ThreadPoolExecutor(max_workers=3) as executor:
        for voc in executor.map(partial(compute_lat_vocab, min_post=min_post), fns):
            vocabs.append(voc)
    return vocabs


def compute_lat_vocab(aligned_lat_fn, min_post=0.0001):
    model_dir = os.environ['MODEL_DIR']
    lang_dir = os.environ['LANG_DIR']
    gunzip_p = subprocess.Popen(('gunzip', '-c', aligned_lat_fn), stdout=subprocess.PIPE)
    arc_post_p = subprocess.Popen(('lattice-arc-post',
                                   '--min-post={}'.format(min_post),
                                   '{}/final.mdl'.format(model_dir),
                                   'ark:-',
                                   '-'),
                                  stdin=gunzip_p.stdout,
                                  stdout=subprocess.PIPE)
    int2sym_p = subprocess.Popen(('int2sym.pl', '-f', '5', '{}/words.txt'.format(lang_dir)),
                                  stdin=arc_post_p.stdout,
                                  stdout=subprocess.PIPE)
    out_posts, _ = int2sym_p.communicate()
    code = int2sym_p.wait()
    if code != 0:
        raise Exception('Failed to convert to ctms')
    arc_posts = convert_arc_posts_file(out_posts.decode('utf-8').split('\n'))
    return arc_posts


def read_utt_posts(posts):
    words = defaultdict(lambda: defaultdict(list))
    for line in posts:
        if len(line.strip()) < 1:
            continue
        fields = line.strip().split()
        utt_id = fields[0]
        word = fields[4]
        post = float(fields[3])

        words[utt_id][word].append(post)

    return words


def convert_arc_posts_file(f):
    posts = []

    all_words = read_utt_posts(f)
    for utt_id, words in all_words.items():
        for i (word, posts) in enumerate(words.items()):
            max_post = np.map(posts)
            posts.append((utt_id, word, max_post))
    return posts


def compute_nbest_lists(fns, n=10):
    nbest_list = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        for nbest in executor.map(partial(compute_nbest_list, n=n), fns):
            nbest_list.extend(nbest)
    return nbest_list


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
    indir = sys.argv[1]
    with tempfile.TemporaryDirectory() as outdir:
        aligned_lat_fns = list(write_aligned_lats(indir, outdir))
#        with tempfile.TemporaryDirectory() as slfoutdir:
#            slf_fns = list(write_slfs(aligned_lat_fns, slfoutdir))
#            for fn in slf_fns[:10]:
#                print(fn)
#            ngrams = compute_ngrams(slf_fns, n=3)
#            for gram in ngrams[:2]:
#                for g in gram[:2]:
#                    print(g)
#        ctms = one_best_ctms(aligned_lat_fns)
#        for ctm in ctms[:2]:
#            for row in ctm[:3]:
#                print(row)
        vocab = compute_vocab(aligned_lat_fns, min_post=0.0001)
        for vocab_lst in vocab[:2]:
            for arc in vocab_lst[:3]:
                print(arc)
#        nbest_lists = compute_nbest_lists(aligned_lat_fns[:1], n=200)
#        for hyp in nbest_lists[:3]:
#                print(hyp)


if __name__ == '__main__':
    main()
