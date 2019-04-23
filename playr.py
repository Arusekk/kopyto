#!/usr/bin/env python3

import argparse, math, os, tempfile, subprocess

def approx1(f):
    arr = []
    while f:
        arr.append(math.floor(f))
        f -= arr[-1]
        if f:
            f = 1/f
        if f>1e7:
            break
    return arr

def approx(f):
    a = approx1(f)[::-1]
    x,y = 0,1
    for i in a:
        x,y = y,x+i*y
    return y,x

def NWD(a, *x):
    return (NWD(x[0]%a, a, *x[1:]) if a else NWW(*x)) if len(x) else a

def prod(l, start=1):
    for x in l: start *= x
    return start

def NWW(*x):
    return prod(x)//NWD(*x)

class Generator:
    def __init__(self, player_class):
        self.player = player_class()
        self._generated = None
        self._formatted = None
        self.params = {}
        self.acc_pos = 0
        self.acc_pos2 = 0

    def feed(self, f):
        self.params.clear()

        for line in f:
            par = line.split()
            if len(par) > 1 and not par[0].startswith('#'):
                self.params[par[0]] = par[1:]

    @property
    def generated(self):
        if not self._generated:
            self._generated = self.regenerate()
        return self._generated

    @property
    def formatted(self):
        if not self._formatted:
            f = self.format()
            self._formatted = self.header % self.params
            self._formatted += f
            self._formatted += self.footer
        return self._formatted

    def play(self):
        self.player.play(self.generated)

class LilypondGenerator(Generator):
    header = r'''
\version "2.19"
bpm = \tempo 4 = %(bpm)s
\score { <<
    \chords {
        \bpm
        \transposition %(ton)s
        \repeat unfold 16 {
%(chords)s
        }
    }
    \new Staff {
        \bpm
        \transposition %(ton)s
        \repeat unfold 16 {
'''
    footer = r'''
    } } >>
    \midi {}
}
'''

    degs = sum(([n+"'"*i for n in 'cdefgab'] for i in range(1,3)), ["gis'"]) + ["fis'"]
    accs = ('e%(dur)s',)+('c%(dur)s','d%(dur)s:m','e%(dur)s:m','f%(dur)s','g%(dur)s','a%(dur)s:m','b%(dur)s:dim')*2+('fis%(dur)s:dim',)

    def transton(self, t):
        return t.replace('x', '##').replace('#','is').replace('b','es').lower()

    def pos2acc(self, pos):
        n = int(self.params['deg'][pos%len(self.params['deg'])])
        if n == 0:
            return 3, 0, 7
        if n == -1:
            return -1, 6, 8
        xdd = int(''.join(self.params['xdd']))
        if n != xdd and n < 2: n += 7
        l = range(n, n+7, 2)
        if n == xdd:
            return l[2], l[0]+7, l[1]+7
        return l

    def pos2dur(self, pos):
        return float(self.params['med'][pos%len(self.params['med'])])

    def float2dur(self, f):
        return '4*%d/%d'%approx(f)

    def mel2ton(self, mm):
        i,m = mm
        m = int(m)-1
        x = self.pos2acc(self.acc_pos2)[m % 3]
        x += (m // 3) * 7
        y = self.pos2dur(i)
        self.acc_pos += y
        while self.acc_pos >= float(self.params['dur'][self.acc_pos2]):
            self.acc_pos -= float(self.params['dur'][self.acc_pos2])
            self.acc_pos2 += 1
            self.acc_pos2 %= len(self.params['dur'])
        debugstr = '' # '%%{ a=%(acc_pos)r, a2=%(acc_pos2)r %%}'
        return self.degs[x]+self.float2dur(y) + debugstr%self.__dict__

    def acc2acc(self, aa):
        i, a = aa
        a = int(a)
        return self.accs[a]%{'dur':self.float2dur(int(self.params['dur'][i%len(self.params['dur'])]))}

    def format(self):
        self.params['ton'] = self.transton(''.join(self.params.get('ton', 'C')))
        self.params['bpm'] = int(''.join(self.params.get('bpm', '120')))
        if 'acc' in self.params:
            self.params['deg'] = self.params['acc']
            self.params['chords'] = ' '.join(map(self.acc2acc, enumerate(self.params['deg']*4)))
        else:
            self.params['chords'] = ''
        self.params['dur'] *= len(self.params['deg'])
        return ' '.join(map(self.mel2ton, enumerate(self.params['mel'] * 2 *
            NWW(len(self.params['med']), len(self.params['dur']), len(self.params['deg']))
            )))

    def regenerate(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ifn = os.path.join(tmpdir, "music.ly")
            with open(ifn, 'wt') as fp:
                fp.write(self.formatted)
            pro = subprocess.Popen(["lilypond", ifn], cwd=tmpdir)
            pro.wait()
            with open(os.path.join(tmpdir, "music.midi"), 'rb') as fp:
                return fp.read()


class TimidityPlayer:
    def play(self, stuff):
        pro = subprocess.Popen(["timidity", "-"], stdin=subprocess.PIPE)
        pro.communicate(stuff)


if __name__=="__main__":
    par = argparse.ArgumentParser()
    par.add_argument("input", type=open)
    par.add_argument("--only-print", "-p", action='store_true')
    
    args = par.parse_args()

    pla = LilypondGenerator(TimidityPlayer)
    with args.input as f:
        pla.feed(f)
    if args.only_print:
        print(pla.formatted)
    else:
        pla.play()

