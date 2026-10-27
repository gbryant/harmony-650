#!/usr/bin/env python3
"""Recover the Harmony 650 config's character codes by solving a substitution
cipher over its strings with a dictionary. charmap_solve.py config_binary"""
import collections, re, sys

cfg = open(sys.argv[1], 'rb').read()
words = set(w.strip().lower() for w in open('/usr/share/dict/words') if w.strip().isalpha())
words |= {'tv', 'dvd', 'cd', 'vcr', 'aux', 'usb', 'ok', 'pc', 'av', 'harmony', 'logitech', 'remote',
          'activity', 'activities', 'devices', 'device', 'watch', 'music', 'listen', 'help', 'input',
          'inputs', 'volume', 'channel', 'menu', 'guide', 'power', 'options', 'press', 'button'}

# Strings: runs of codes in 0x01..0x7F terminated by 0x00, at least 3 long
strings = [m.group(0) for m in re.finditer(rb'[\x01-\x7f]{3,}(?=\x00)', cfg)]
known = {0x05: ' ', 0x07: 's', 0x08: 'e', 0x15: 'a', 0x17: 't', 0x1a: 'm', 0x1b: 'o',
         0x1c: 'n', 0x22: 'A', 0x23: 'i', 0x2f: 'R', 0x19: 'r'}

def tokens():
    for s in strings:
        for t in s.split(b'\x05'):
            if 2 <= len(t) <= 14:
                yield t
toks = collections.Counter(tokens())

def candidates(tok, mp):
    inv = {v.lower(): k for k, v in mp.items()}
    pat = [tok.index(c) for c in tok]
    out = []
    for w in bywlen.get(len(tok), ()):
        if [w.index(c) for c in w] != pat:
            continue
        ok = True
        for c, ch in zip(tok, w):
            if c in mp and mp[c].lower() != ch:
                ok = False; break
            if c not in mp and ch in inv and inv[ch] != c:
                ok = False; break
        if ok:
            out.append(w)
    return out

bywlen = collections.defaultdict(list)
for w in words:
    bywlen[len(w)].append(w)

mp = dict(known)
for _ in range(30):
    votes = collections.defaultdict(collections.Counter)
    for tok, n in toks.items():
        unknown = [c for c in set(tok) if c not in mp]
        if not unknown or len(unknown) > 2 or sum(c in mp for c in tok) < 2:
            continue
        cs = candidates(tok, mp)
        if len(cs) == 1:
            for c, ch in zip(tok, cs[0]):
                if c not in mp:
                    votes[c][ch] += n
    added = False
    for c, cnt in votes.items():
        ch, v = cnt.most_common(1)[0]
        if v >= 3 and v >= 2 * sum(x for k, x in cnt.items() if k != ch) and ch not in [x.lower() for x in mp.values()]:
            mp[c] = ch; added = True
    if not added:
        break

for c in sorted(mp):
    print('%02X %r' % (c, mp[c]))
print('--- sample decodes')
dec = lambda s: ''.join(mp.get(c, '·') for c in s)
for s in sorted(set(strings), key=lambda s: -sum(c in mp for c in s) / len(s))[:40]:
    print(dec(s))
