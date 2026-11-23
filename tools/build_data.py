#!/usr/bin/env python3
"""Builds offline data from an OSM extract:
   <name>.graph - compact road graph for the in-app router
   <name>.tsv   - place/street/POI names for offline Arabic search (one line per place)
Usage: python build_data.py extract.pbf [name]      (name defaults to "ksa")"""
import sys, os, re, math, array
import numpy as np, osmium

SPEED = {'motorway': 100, 'trunk': 90, 'primary': 70, 'secondary': 60, 'tertiary': 50, 'unclassified': 40,
         'residential': 35, 'living_street': 15, 'service': 20, 'motorway_link': 60, 'trunk_link': 55,
         'primary_link': 50, 'secondary_link': 45, 'tertiary_link': 40, 'road': 30}
PLACE = {'city', 'town', 'village', 'hamlet', 'suburb', 'neighbourhood', 'quarter', 'locality', 'island'}
POI = ('amenity', 'shop', 'tourism', 'historic', 'leisure', 'aeroway', 'natural')
TR = str.maketrans({'أ': 'ا', 'إ': 'ا', 'آ': 'ا', 'ى': 'ي', 'ة': 'ه'})
def norm(s): return re.sub('[\u064B-\u0652\u0640]', '', s).lower().translate(TR)   # same rules as the app
def usable(t): return t.get('highway') in SPEED and t.get('access') not in ('no', 'private') and t.get('area') != 'yes'
def hav(a, b): return math.hypot((b[2] - a[2]) * 110540, (b[1] - a[1]) * 111320 * math.cos(math.radians(a[2])))
def oneway(t, h):
    o = t.get('oneway')
    if o in ('yes', '1', 'true'): return 1
    if o == '-1': return -1
    return 1 if h in ('motorway', 'motorway_link') or t.get('junction') == 'roundabout' else 0

class Count(osmium.SimpleHandler):            # pass 1: which nodes are junctions
    def __init__(s): super().__init__(); s.a = array.array('q')
    def way(s, w):
        if usable(w.tags): s.a.extend([n.ref for n in w.nodes])

class Build(osmium.SimpleHandler):            # pass 2: edges + names
    def __init__(s, inter, tsv):
        super().__init__(); s.inter = inter; s.idx = {}; s.lat = array.array('i'); s.lon = array.array('i')
        s.E = array.array('q'); s.nrows = 0; s.seen = set(); s.tsv = tsv; s.cnt = 0   # flat arrays: ~10x less RAM than lists of tuples
    def ni(s, p):
        i = s.idx.get(p[0])
        if i is None:
            i = len(s.lat); s.idx[p[0]] = i; s.lat.append(round(p[2] * 1e6)); s.lon.append(round(p[1] * 1e6))
        return i
    def add(s, nm, kind, lat, lon, dedupe=False):
        if dedupe:
            k = hash((nm, round(lat, 2), round(lon, 2)))   # store only the hash, not the tuple
            if k in s.seen: return
            s.seen.add(k)
        s.tsv.write('%s\t%s\t%s\t%.5f\t%.5f\n' % (norm(nm).replace('\t', ' ').replace('\n', ' '), nm.replace('\t', ' ').replace('\n', ' '), kind, lat, lon))
        s.nrows += 1   # streamed straight to disk instead of kept in memory
    def node(s, n):
        s.cnt += 1
        if s.cnt % 5000000 == 0: print('  ..', s.cnt // 1000000, 'M nodes read', flush=True)
        t = n.tags; nm = t.get('name:ar') or t.get('name')
        if not nm: return
        if t.get('place') in PLACE: k = 'place'
        elif any(x in t for x in POI): k = 'poi'
        else: return
        s.add(nm, k, n.location.lat, n.location.lon)
    def way(s, w):
        t = w.tags
        if not usable(t): return
        try: p = [(n.ref, n.lon, n.lat) for n in w.nodes]
        except Exception: return
        if len(p) < 2: return
        nm = t.get('name:ar') or t.get('name'); h = t['highway']
        if nm: s.add(nm, 'road', p[len(p) // 2][2], p[len(p) // 2][1], True)
        sp = SPEED[h]; m = re.match(r'\d+', t.get('maxspeed', ''))
        if m: sp = max(5, min(int(m.group()), 130))
        ow = oneway(t, h); ff = 256 if ow == -1 else 0; rf = 256 if ow == 1 else 0   # bit 256 = car may not use this direction
        a = s.ni(p[0]); acc = 0.0
        for k in range(1, len(p)):
            acc += hav(p[k - 1], p[k])
            if k == len(p) - 1 or p[k][0] in s.inter or acc >= 250:   # keep junctions + a node every ~250 m
                b = s.ni(p[k]); L = int(acc) + 1
                s.E.extend((a, b, L, sp | ff, b, a, L, sp | rf)); a = b; acc = 0.0

src = sys.argv[1]; name = sys.argv[2] if len(sys.argv) > 2 else 'ksa'
print(name, ': pass 1 (counting junctions)', flush=True)
c = Count(); c.apply_file(src)
ids, cnt = np.unique(np.frombuffer(c.a, dtype=np.int64), return_counts=True)
inter = set(ids[cnt >= 2].tolist()); del c, ids, cnt
print(name, ': pass 2 (edges + names)', flush=True)
tmp = name + '.tsv.part'
with open(tmp, 'w', encoding='utf-8') as tsv:   # for the web app (one line per place)
    b = Build(inter, tsv); b.apply_file(src, locations=True)
n = len(b.lat); del inter, b.idx, b.seen
if not len(b.E):
    os.remove(tmp); print(name, ': no usable roads in this area - nothing written'); sys.exit(0)
E = np.frombuffer(b.E, dtype=np.int64).reshape(-1, 4); E = E[np.argsort(E[:, 0], kind='stable')]
off = np.searchsorted(E[:, 0], np.arange(n + 1))
with open(name + '.graph', 'wb') as f:
    np.array([0x4B534147, n, len(E)], '>i4').tofile(f)
    for arr in (np.frombuffer(b.lat, dtype=np.int32), np.frombuffer(b.lon, dtype=np.int32), off, E[:, 1], E[:, 2], E[:, 3]): arr.astype('>i4').tofile(f)
os.replace(tmp, name + '.tsv')
print(name, ': nodes', n, 'edges', len(E), 'places', b.nrows, flush=True)
