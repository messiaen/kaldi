import sys
import os
import gzip
from collections import defaultdict
import numpy as np


def read_stm_times(stm):
    times = {}
    for line in filter(lambda l: len(l) > 0, stm):
        if line.startswith(';;'):
            continue
        fields = line.strip().split()
        audio_id = fields[0]
        channel = fields[1]
        start = float(fields[3])
        end = float(fields[4])
        words = fields[6:]

        times[audio_id] = (start, end)

    return times


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


def convert(v_audio_id, times, words, outfile):
    edges = []
    for i, (word, posts) in enumerate(words.items()):
        max_post = np.max(posts)
        edges.append('J={0}\tS=0\tE=1\tW={1}\tv=0.000000\ta=0.0\tl=0.0\ts={2}'.format(int(i), word, max_post))
    version = 'VERSION=1.1\n'
    uttr = 'UTTERANCE={}\n'.format(v_audio_id)
    info = 'N=2\tL={}\n'.format(len(edges))
    n1 = 'I=0\tt={}\n'.format(times[0])
    n2 = 'I=1\tt={}\n'.format(times[1])

    outfile.write(version)
    outfile.write(uttr)
    outfile.write(info)
    outfile.write(n1)
    outfile.write(n2)
    outfile.write('\n'.join(edges))


def write_cnet_lst(outdir):
    with open(os.path.join(outdir, 'cnet.lst'), 'w') as cnet_f:
        for fn in os.listdir(outdir):
            if os.path.isfile(os.path.join(outdir, fn)) and fn.endswith('.slf.gz'):
                cnet_f.write(os.path.abspath(os.path.join(outdir, fn)) + '\n')


def main():
    stm_fn = sys.argv[1]
    indir = sys.argv[2]
    outdir = sys.argv[3]

    with open(stm_fn, 'r', encoding='utf-8') as f:
        times = read_stm_times(f)

    for fn in os.listdir(indir):
        if os.path.isfile(os.path.join(indir, fn)):
            with gzip.open(os.path.join(indir, fn), 'rt', encoding='utf-8') as inf:
                words = read_utt_posts(inf)
            for utt_id, word_d in words.items():
                with gzip.open(os.path.join(outdir, '.'.join((utt_id, 'slf', 'gz'))), 'wt', encoding='utf-8') as outf:
                    convert(utt_id, times[utt_id], word_d, outf)
    write_cnet_lst(outdir)


if __name__ == "__main__":
    main()
