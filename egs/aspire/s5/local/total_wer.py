import sys
import os

def extract_wer(fn):
    with open(fn, 'r') as f:
        for _line in f:
            line = _line.strip()
            if len(line) < 1:
                continue
            if 'WER' in line:
                print(line)


def main():
    d = sys.argv[1]
    for fn in os.listdir(d):
        if 'wer' in fn:
            extract_wer(os.path.join(d, fn))


if __name__ == '__main__':
    main()
