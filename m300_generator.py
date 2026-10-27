# notes_to_gcode.py
# Usage: python notes_to_gcode.py MACRO_NAME "E5 G5:2 D5 R C5"
#        python notes_to_gcode.py MACRO_NAME song.txt
#   NOTE[:beats]  e.g. E5, F#4, Bb4, G5:2 (2 beats), R = rest
#   -  = hold previous note one more beat
#   |  = bar line (ignored, for readability)
import sys, os

NAMES = {"C":0,"D":2,"E":4,"F":5,"G":7,"A":9,"B":11}
BEAT_MS = 375  # 1 beat; lower = faster (375 matches your Simpsons quarter note)

def freq(note):
    n = NAMES[note[0].upper()]
    rest = note[1:]
    if rest[0] == "#": n += 1; rest = rest[1:]
    elif rest[0] == "b": n -= 1; rest = rest[1:]
    midi = 12 * (int(rest) + 1) + n
    return round(440 * 2 ** ((midi - 69) / 12))

name, src = sys.argv[1], sys.argv[2]
if os.path.isfile(src):
    with open(src) as f:
        src = f.read()

events = []  # [freq, beats]
for tok in src.split():
    if tok == "|":
        continue
    if tok == "-":
        if events:
            events[-1][1] += 1
        continue
    t, _, beats = tok.partition(":")
    f = 0 if t.upper() == "R" else freq(t)
    events.append([f, float(beats or 1)])

print(f"[gcode_macro {name}]\ngcode:")
for f, beats in events:
    print(f"    M300 P{round(BEAT_MS * beats)} S{f}")
