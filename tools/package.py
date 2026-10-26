#!/usr/bin/env python3
"""Packs a converted profile pack (tools/convert.py) and the community data for download (docs/FORMAT.md,
"Descarga"): one compressed archive per vendor bundle and one for the community data, plus a small index that lists
them with their size and SHA-256.

Usage: package.py <pack dir> <community dir> <out dir> --version VERSION
"""

import argparse
import hashlib
import json
import lzma
import os
import shutil
import tarfile


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def tar_xz(out, root, names):
    with lzma.open(out, 'wb', preset=9) as raw, tarfile.open(fileobj=raw, mode='w') as tar:
        for name in names:
            tar.add(os.path.join(root, name), arcname=name, recursive=True,
                    filter=lambda t: (setattr(t, 'mtime', 0), setattr(t, 'uid', 0), setattr(t, 'gid', 0),
                                      setattr(t, 'uname', ''), setattr(t, 'gname', ''), t)[-1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pack')
    ap.add_argument('community')
    ap.add_argument('out')
    ap.add_argument('--version', required=True)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    index = json.load(open(os.path.join(args.pack, 'index.json'), encoding='utf-8'))
    index['pack_version'] = args.version
    for v in index['vendors']:
        name = v['id'] + '.tar.xz'
        path = os.path.join(args.out, name)
        tar_xz(path, args.pack, [os.path.join('vendors', v['id'])])
        v['archive'] = {'name': name, 'size': os.path.getsize(path), 'sha256': sha256(path)}

    shutil.copyfile(os.path.join(args.pack, 'compatible.json'), os.path.join(args.out, 'compatible.json'))
    index['compatible'] = {'name': 'compatible.json', 'size': os.path.getsize(os.path.join(args.out, 'compatible.json')),
                           'sha256': sha256(os.path.join(args.out, 'compatible.json'))}

    community = [n for n in sorted(os.listdir(args.community)) if os.path.isdir(os.path.join(args.community, n))]
    path = os.path.join(args.out, 'community.tar.xz')
    tar_xz(path, os.path.dirname(os.path.abspath(args.community)),
           [os.path.join(os.path.basename(os.path.abspath(args.community)), n) for n in community])
    index['community'] = {'name': 'community.tar.xz', 'size': os.path.getsize(path), 'sha256': sha256(path)}

    with open(os.path.join(args.out, 'index.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(index, f, ensure_ascii=False, separators=(',', ':'))
    total = sum(os.path.getsize(os.path.join(args.out, n)) for n in os.listdir(args.out))
    print('%d files, %.1f MB' % (len(os.listdir(args.out)), total / 1e6))


if __name__ == '__main__':
    main()
