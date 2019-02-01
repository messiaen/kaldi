import sys
import re
import json
import os
import errno
import logging
import subprocess
import codecs
import math
import pywrapfst as fst


logger = logging.getLogger()


framerate = 0.03


def make_dirs(dirname):
    try:
        os.makedirs(dirname)
    except OSError as exc:
        if exc.errno != errno.EEXIST:
            raise


def create_sausage(lat_fn, text_fn, mbr_fn, sau_fn, times_fn):
    model_dir = os.environ['MODEL_DIR']
    lang_dir = os.environ['LANG_DIR']
    gunzip_p = subprocess.Popen(('gunzip', '-c', lat_fn), stdout=subprocess.PIPE)
    lattice_scale_p = subprocess.Popen(('lattice-scale',
                                        '--lm-scale=1.0',
                                        'ark:-',
                                        'ark:-'),
                                       stdin=gunzip_p.stdout,
                                       stdout=subprocess.PIPE)
    align_lattice_p = subprocess.Popen(('lattice-align-words',
                                        '{}/phones/word_boundary.int'.format(lang_dir),
                                        '{}/final.mdl'.format(model_dir),
                                        'ark:-',
                                        'ark:-'),
                                       stdin=lattice_scale_p.stdout,
                                       stdout=subprocess.PIPE)
    mbr_decode_p = subprocess.Popen(('lattice-mbr-decode',
                                     'ark:-',
                                     'ark,t:|int2sym.pl -f 2- {}/words.txt > {}'.format(lang_dir, text_fn),
                                     'ark,t:{}'.format(mbr_fn),
                                     'ark,t:{}'.format(sau_fn),
                                     'ark,t:{}'.format(times_fn)),
                                    stdin=align_lattice_p.stdout)
    mbr_decode_p.wait()

    return text_fn, sau_fn, times_fn


def read_sau(f, word_syms):
    utterances = {}
    link_pat = re.compile(r'\[[e\-0-9\.\ ]+\]')
    for _line in f:
        line = _line.strip()
        if len(line) < 1:
            continue
        utt_id = line.split(' ', 1)[0]
        links = re.findall(link_pat, line)
        utt_links = []
        for _link in links:
            link = _link.split()[1:-1]
            link_words = []
            for word_id, post_str in zip(*[iter(link)] * 2):
                word = word_syms[word_id]
                post = float(post_str)
                link_words.append((word, post))
            utt_links.append(link_words)
        utterances[utt_id] = utt_links
    return utterances


def read_times(f):
    utterances = {}
    for _line in f:
        line = _line.strip()
        if len(line) < 1:
            continue
        utt_id, rest = line.split(' ', 1)
        # TODO make this work with librispeech and callhome
        # librispeech does not put times in utt_id
        #utt_start, utt_stop = (float(s.lstrip('0')) / 100.0 for s in utt_id.split('-')[-2:])
        time_pairs = [tuple(map(lambda x: 0.0 + float(x) * framerate, p.strip().split())) for p in rest.split(';')]
        utterances[utt_id] = time_pairs
    return utterances


def correlate(sau, times):
    utterances = {}
    for utt_id, links in sorted(sau.iteritems(), key=lambda x: x[0]):
        utterance = []
        #assert len(times[utt_id]) == len(links)
        for i, link in enumerate(links):
            utt_link = []
            for rank, arc in enumerate(link, 1):
                utt = {
                        "utterance_id": utt_id,
                        "position": i,
                        "start": times[utt_id][i][0],
                        "stop": times[utt_id][i][1],
                        "rank": rank,
                        "name": arc[0],
                        "score": arc[1]
                    }
                utt_link.append(utt)
            utterance.append(utt_link)
        utterances[utt_id] = utterance
    return utterances


def utt_to_fst(utt, syms):
    f = fst.Fst()
    start = f.add_state()
    f.set_start(start)

    last_state = start
    for link in utt:
        next_state = f.add_state()
        for word in link[:100]:
            w = int(syms[word['name']])
            weight = -word['score']
            f.add_arc(last_state, fst.Arc(w, w, weight, next_state))
        last_state = next_state
    f.set_final(last_state)
    return f


def read_word_syms(f):
    syms = {}
    for _line in f:
        line = _line.strip()
        if len(line) < 1:
            continue
        word, sym = line.split()
        syms[sym] = word
    return syms


def to_docs(lat_fn, outdir):
    lang_dir = os.environ['LANG_DIR']

    lat_n = os.path.basename(lat_fn).split('.')[1]
    lat_dir = os.path.dirname(lat_fn)
    text_fn = os.path.join(lat_dir, 'text.{}'.format(lat_n))
    mbr_fn = os.path.join(lat_dir, 'mbr.{}'.format(lat_n))
    sau_fn = os.path.join(lat_dir, 'sau.{}'.format(lat_n))
    times_fn = os.path.join(lat_dir, 'times.{}'.format(lat_n))

    create_sausage(lat_fn, text_fn, mbr_fn, sau_fn, times_fn)
    with codecs.open(os.path.join(lang_dir, 'words.txt'), 'r', encoding='utf-8') as f:
        syms = read_word_syms(f)
    wordsyms = {w: s for s, w in syms.iteritems()}
    with codecs.open(sau_fn, 'r', encoding='utf-8') as f:
        sau = read_sau(f, syms)
    with codecs.open(times_fn, 'r', encoding='utf-8') as f:
        times = read_times(f)

    utterances = correlate(sau, times)
    nbest_utterances = {}
    for utt_id, links in utterances.iteritems():
        f = utt_to_fst(links, wordsyms)
        f = fst.shortestpath(f, nshortest=100, unique=True)
        #f = fst.push(f, push_weights=True)
        paths = []
        utt_times = times[utt_id]
        for arc in f.arcs(f.start()):
            path_weight = float(arc.weight.to_string())
            path = [{'word': syms[str(arc.olabel)], 'score': path_weight}]
            a = arc
            while f.final(a.nextstate).to_string() == 'Infinity':
                a = next(f.arcs(a.nextstate))
                w = float(a.weight.to_string())
                path.append({'word': syms[str(a.olabel)], 'score': -w})
                path_weight += w

            if len(path) > 3:
                path_w_times = []
                for i in range(2, len(path)-1):
                    path_w_times.append({
                        'word': path[i]['word'],
                        'score': path[i]['score'],
                        'start': utt_times[i-2][0],
                        'stop': utt_times[i-2][1]})
                    #path_w_times.append((syms[str(path[i])], utt_times[i-2]))
                #path_weight = 10 ** (-path_weight / float(max(1, len(path) - 3)))
                path_weight = -path_weight / float(len(path) - 3)
                paths.append({
                    'score': path_weight,
                    'path': path_w_times})

            #path_weight += float(f.final(a.nextstate).to_string())
            #path_string = ' '.join([syms[str(s)] for s in path if s != 0 and syms[str(s)] != '<unk>'])
            #paths.append((path_weight, path_string))
        nbest_utterances[utt_id] = [{'score': p['score'], 'path': p['path'], 'rank': r} for r, p in enumerate(sorted(paths, key=lambda x: -x['score']), 1)]

    for utt_id, links in utterances.iteritems():
        doc_dir = os.path.join(outdir, '-'.join(utt_id.split('-')[:2]))
        utt_fn = os.path.join(doc_dir, '{}.json'.format(utt_id))
        logger.debug('Writing utterance: {} to {}'.format(utt_id, utt_fn))
        make_dirs(doc_dir)
        with codecs.open(utt_fn, 'w', encoding='utf-8') as f:
            u = {'links': links, 'nbest': nbest_utterances.get(utt_id, [])}
            json.dump(u, f, indent=4, ensure_ascii=False)


if __name__ == '__main__':
    lat_fn = sys.argv[1]
    outdir = sys.argv[2]

    to_docs(lat_fn, outdir)
