#!/usr/bin/env python3
"""Builds _site/: web app files + data split into 24 MB parts (served by GitHub Pages) + data/manifest.json"""
import os, json, shutil, time
SITE = '_site'; os.makedirs(SITE + '/data', exist_ok=True)
for f in ['index.html', 'sw.js', 'manifest.webmanifest', 'icon-192.png', 'icon-512.png']: shutil.copy(f, SITE)
man = {'v': int(time.time()), 'files': {}}
for name in ('places.tsv', 'ksa.graph'):
    p = os.path.join('dl', name)
    if not os.path.exists(p): continue
    parts = []; i = 0
    with open(p, 'rb') as f:
        while True:
            b = f.read(24 * 1024 * 1024)
            if not b: break
            pn = '%s.%03d' % (name, i); open(os.path.join(SITE, 'data', pn), 'wb').write(b); parts.append(pn); i += 1
    man['files'][name] = {'size': os.path.getsize(p), 'parts': parts}
if len(man['files']) == 2: json.dump(man, open(SITE + '/data/manifest.json', 'w'))
else: print('No offline data published yet - deploying the app without it.')
