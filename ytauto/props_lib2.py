"""Prop library part 2: people & feelings, mystery & crime, symbols, communication, school, everyday objects."""
import math

from .props import prop, rot, scale, wave


# ============================================================================================ PEOPLE / FEELINGS
@prop("heart", "love, heart, hearts, like, likes, romance, romantic, relationship, dating, crush, health, care, valentine", "people")
def _(P):
    k = 1 + 0.07 * max(0, math.sin(P.t * 7)) * (1 if int(P.t * 1.2) % 2 == 0 else 0.4)
    pts = []
    for i in range(36):
        a = i / 36 * 2 * math.pi
        x = 16 * math.sin(a) ** 3
        y = -(13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a))
        pts.append((50 + x * 2.3 * k, 48 + y * 2.3 * k))
    P.poly(pts, w=3.6, fill="red")
    P.arc(38, 36, 8, 8, 200, 260, w=2.4, color="white")


@prop("broken_heart", "breakup, broke up, heartbreak, heartbroken, divorce, betrayal, cheated, sad love, ex, dumped", "people")
def _(P):
    def half(sign, dx):
        pts = []
        for i in range(19):
            a = (i / 18 * math.pi) * (1 if sign > 0 else -1)
            x = 16 * math.sin(a) ** 3
            y = -(13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a))
            pts.append((50 + x * 2.3 + dx, 48 + y * 2.3))
        crack = [(50 + dx, 82), (46 + dx, 66), (54 + dx, 54), (46 + dx, 42), (50 + dx, 28)]
        return pts + (crack if sign > 0 else crack[::-1])
    sep = min(4, P.t * 4)
    P.poly(half(1, sep), w=3.4, fill="red")
    P.poly(half(-1, -sep), w=3.4, fill="red")


@prop("eye", "eye, eyes, see, seen, watch, watching, vision, look, looking, spy, surveillance, witness, observe, saw, sighting", "people")
def _(P):
    blink = (int(P.t * 12) % 40) < 2
    if blink:
        P.curve([(10, 50), (50, 62), (90, 50)], w=3.6)
        return
    P.poly([(10, 50), (30, 32), (50, 27), (70, 32), (90, 50), (70, 68), (50, 73), (30, 68)], w=3.6, fill="white", smooth=True)
    lx = wave(P.t, 1.3, 9)
    P.circle(50 + lx, 50, 15, w=3, fill="blue")
    P.circle(50 + lx, 50, 7, w=2, fill="black")
    P.dot(46 + lx, 46, 2.4, color="white")
    for x in (24, 38, 50, 62, 76):
        P.line(x, 34 - (6 if x == 50 else 4), x, 30 - (10 if x == 50 else 6), w=2.4)


@prop("thumbs_up", "like, good, great, approve, approved, yes, agree, recommend, nice, awesome, thumbs up, well done, ok", "people")
def _(P):
    b = abs(math.sin(P.t * 3)) * 3
    P.rrect(12, 46 - b, 30, 88 - b, r=3, w=3.2, fill="blue")
    P.blob([(30, 50 - b), (46, 34 - b), (50, 14 - b), (60, 16 - b), (60, 38 - b), (82, 40 - b), (86, 50 - b), (82, 86 - b),
            (30, 86 - b)], w=3.4, fill="skin")
    for y in (52, 64, 75):
        P.line(68, y - b, 84, y - b, w=2.2)


@prop("thumbs_down", "dislike, bad, terrible, disapprove, no way, thumbs down, fail, boo, worst, rejected", "people")
def _(P):
    b = abs(math.sin(P.t * 3)) * 3
    P.rrect(12, 12 + b, 30, 54 + b, r=3, w=3.2, fill="red")
    P.blob([(30, 50 + b), (46, 66 + b), (50, 86 + b), (60, 84 + b), (60, 62 + b), (82, 60 + b), (86, 50 + b), (82, 14 + b),
            (30, 14 + b)], w=3.4, fill="skin")
    for y in (48, 36, 25):
        P.line(68, y + b, 84, y + b, w=2.2)


@prop("muscle", "strong, strength, gym, fitness, workout, exercise, muscle, muscles, power, powerful, flex, bodybuilding, tough", "people")
def _(P):
    k = 1 + 0.08 * max(0, math.sin(P.t * 4))
    P.rect(2, 60, 14, 88, w=3, fill="blue")
    P.poly([(12, 62), (52, 58), (60, 76), (12, 88)], w=3.4, fill="skin")
    P.poly([(46, 66), (52, 24), (70, 24), (64, 72)], w=3.4, fill="skin")
    P.circle(61, 18, 12, w=3.4, fill="skin")
    P.curve([(54, 14), (58, 20), (64, 18)], w=2)
    P.blob(scale([(18, 62), (24, 44), (38, 38), (50, 46), (50, 62)], 34, 56, k), w=3.2, fill="skin")
    P.curve([(28, 50), (36, 46), (42, 52)], w=2)
    for i, (x, y) in enumerate(((26, 30), (36, 24), (18, 38))):
        if (int(P.t * 4) + i) % 2 == 0:
            P.line(x, y, x - 5, y - 5, w=2.4, color="orange")


@prop("crowd", "people, crowd, crowds, population, society, followers, audience, public, everyone, community, citizens, fans, group", "people")
def _(P):
    for i, (x, s, c) in enumerate(((22, 0.8, "teal"), (78, 0.8, "orange"), (50, 1.0, "purple"))):
        bob = wave(P.t, 3, 2, i)
        y0 = 30 + (1 - s) * 30 + bob
        P.circle(x, y0, 11 * s, w=3, fill="white")
        P.blob([(x - 18 * s, y0 + 52 * s), (x - 16 * s, y0 + 20 * s), (x, y0 + 14 * s), (x + 16 * s, y0 + 20 * s),
                (x + 18 * s, y0 + 52 * s)], w=3, fill=c)


@prop("family", "family, parents, mom, dad, mother, father, kids, children, child, siblings, brother, sister, son, daughter", "people")
def _(P):
    for i, (x, h, c) in enumerate(((22, 1.0, "blue"), (46, 0.95, "pink"), (68, 0.65, "green"), (84, 0.55, "yellow"))):
        top = 88 - 70 * h + wave(P.t, 2.5, 1.5, i)
        P.circle(x, top + 8 * h, 8 * h, w=2.8, fill="white")
        P.poly([(x - 9 * h, 88), (x - 7 * h, top + 18 * h), (x + 7 * h, top + 18 * h), (x + 9 * h, 88)], w=2.8, fill=c)
    P.star(56, 12, 5, 4, n=5, w=1.6, fill="red")


@prop("baby", "baby, babies, born, birth, infant, newborn, pregnant, pregnancy, toddler", "people")
def _(P):
    a = wave(P.t, 2, 5)
    P.circle(50, 46, 28, w=3.4, fill="skin")
    P.curve([(46, 18), (52, 12), (56, 18)], w=2.6)
    for x in (40, 60):
        P.arc(x, 44, 4, 3, 200, 340, w=2.6)
    P.circle(50, 58, 5, w=2.4, fill="lightblue")
    P.poly(rot([(30, 74), (70, 74), (76, 92), (24, 92)], 50, 80, a), w=3.2, fill="lightblue")
    P.circle(32, 54, 3.6, w=1.4, fill="pink")
    P.circle(68, 54, 3.6, w=1.4, fill="pink")


@prop("happy_face", "happy, happiness, joy, joyful, smile, smiling, good news, glad, cheerful, positive, grateful", "people")
def _(P):
    P.circle(50, 50, 38, w=3.6, fill="yellow")
    for x in (36, 64):
        P.ellipse(x, 40, 4, 6, w=2.4, fill="ink")
    k = 1 + 0.1 * abs(math.sin(P.t * 3))
    P.arc(50, 52, 22 * k, 18 * k, 20, 160, w=3.6)


@prop("sad_face", "sad, sadness, depressed, depression, crying, cry, tears, unhappy, grief, lonely, miserable, upset, tragic", "people")
def _(P):
    P.circle(50, 50, 38, w=3.6, fill="lightblue")
    for x in (36, 64):
        P.ellipse(x, 42, 4, 5, w=2.4, fill="ink")
    P.arc(50, 76, 18, 12, 200, 340, w=3.6)
    y = 50 + ((P.t * 24) % 30)
    P.blob([(64, y), (61, y + 6), (64, y + 9), (67, y + 6)], w=2, fill="blue")


@prop("angry_face", "angry, anger, mad, furious, rage, annoyed, frustrated, hate, outraged, livid", "people")
def _(P):
    sh = wave(P.t, 25, 1.2)
    P.circle(50 + sh, 50, 38, w=3.6, fill="red")
    P.line(26 + sh, 30, 44 + sh, 40, w=4)
    P.line(74 + sh, 30, 56 + sh, 40, w=4)
    for x in (36, 64):
        P.dot(x + sh, 46, 4)
    P.arc(50 + sh, 76, 16, 10, 200, 340, w=3.6)
    if int(P.t * 3) % 2 == 0:
        P.curve([(84, 12), (90, 8), (92, 14), (88, 18)], w=2.4, color="red")


@prop("shocked_face", "shocked, shock, surprised, surprise, omg, wow, unbelievable, mind blown, amazed, stunned, speechless, scared", "people")
def _(P):
    P.circle(50, 50, 38, w=3.6, fill="yellow")
    for x in (36, 64):
        P.circle(x, 40, 7, w=2.6, fill="white")
        P.dot(x, 40, 3)
    k = 1 + 0.15 * abs(math.sin(P.t * 5))
    P.ellipse(50, 66, 8 * k, 11 * k, w=3.2, fill="black")
    for a in (-60, -30, 0, 30, 60):
        r = math.radians(a - 90)
        P.line(50 + 44 * math.cos(r), 50 + 44 * math.sin(r), 50 + 52 * math.cos(r), 50 + 52 * math.sin(r), w=2.6, color="orange")


@prop("laughing_face", "funny, laugh, laughing, lol, hilarious, joke, jokes, comedy, lmao, humor, meme, memes", "people")
def _(P):
    sh = wave(P.t, 10, 2)
    P.circle(50, 50 + sh, 38, w=3.6, fill="yellow")
    for x in (36, 64):
        P.arc(x, 44 + sh, 7, 6, 200, 340, w=3)
    P.poly([(28, 56 + sh), (72, 56 + sh), (50, 82 + sh)], w=3.2, fill="black", smooth=True)
    P.blob([(18, 50 + sh), (14, 58 + sh), (18, 62 + sh), (22, 56 + sh)], w=2, fill="lightblue")
    P.blob([(82, 50 + sh), (86, 58 + sh), (82, 62 + sh), (78, 56 + sh)], w=2, fill="lightblue")


# ============================================================================================ MYSTERY / CRIME
@prop("skull", "death, dead, deaths, danger, deadly, poison, pirate, die, died, killer, murder, fatal, toxic, lethal, doom", "mystery")
def _(P):
    j = abs(math.sin(P.t * 4)) * 3 if P.t > 0.8 else 0
    P.blob([(50, 12), (74, 18), (84, 38), (78, 58), (68, 64), (32, 64), (22, 58), (16, 38), (26, 18)], w=3.6, fill="white")
    for x in (36, 64):
        P.ellipse(x, 42, 9, 9, w=2.6, fill="black")
    P.poly([(50, 50), (45, 58), (55, 58)], w=2, fill="black")
    P.rrect(34, 66 + j, 66, 82 + j, r=5, w=3.2, fill="white")
    for x in (42, 50, 58):
        P.line(x, 66 + j, x, 82 + j, w=2)


@prop("ghost", "ghost, ghosts, haunted, haunting, spirit, spirits, paranormal, spooky, phantom, poltergeist, apparition, scary", "mystery")
def _(P):
    by = wave(P.t, 2.2, 4)
    pts = [(24, 86 + by), (22, 40 + by), (34, 18 + by), (50, 12 + by), (66, 18 + by), (78, 40 + by), (76, 86 + by)]
    for i in range(4):
        x = 76 - (i + 1) * 13
        pts.append((x + 6.5, 80 + by + wave(P.t, 6, 4, i)))
        pts.append((x, 88 + by))
    P.blob(pts, w=3.4, fill="white")
    for x in (40, 60):
        P.ellipse(x, 42 + by, 4.5, 7, w=2, fill="black")
    P.ellipse(50, 60 + by, 6, 8 * (0.7 + 0.3 * abs(math.sin(P.t * 3))), w=2.4, fill="black")


@prop("footprints", "footsteps, footprints, tracks, trail, walked, walking, missing person, steps, followed, path, last seen, hiking", "mystery")
def _(P):
    n = int(P.t * 2.5) + 1
    spots = [(36, 86, -8), (60, 70, 8), (38, 52, -8), (62, 34, 8), (40, 16, -8)]
    for i, (x, y, a) in enumerate(spots):
        if i >= n and P.t > 0.8:
            break
        sole = [(x - 6, y - 2), (x - 7, y - 9), (x - 4, y - 14), (x + 1, y - 15), (x + 6, y - 12), (x + 7, y - 5), (x + 5, y + 1),
                (x, y + 2)]
        P.poly(rot(sole, x, y, a), w=2.6, fill="brown", smooth=True)
        P.poly(rot([(x - 5, y + 5), (x + 5, y + 5), (x + 5, y + 11), (x - 5, y + 11)], x, y, a), w=2.4, fill="brown", smooth=True)


@prop("fingerprint", "fingerprint, fingerprints, evidence, crime scene, identity, forensic, forensics, clue, clues, dna evidence, suspect", "mystery")
def _(P):
    for i in range(7):
        r = 6 + i * 5
        P.arc(50, 52, r * 0.82, r, 200 - i * 4, 520 - i * 2 - (40 if i % 2 else 0), w=2.6)
    if P.t > 0.9:
        y = 18 + ((P.t * 40) % 70)
        P.line(16, y, 84, y, w=2, color="green")


@prop("magnifier", "search, searching, investigate, investigation, detective, find, research, look closer, examine, mystery, "
      "unsolved, case, inspection, clue hunting", "mystery")
def _(P):
    ox, oy = wave(P.t, 1.6, 6), wave(P.t, 2.1, 5, 1)
    P.circle(42 + ox, 42 + oy, 26, w=4, fill="lightblue")
    P.arc(42 + ox, 42 + oy, 18, 18, 200, 260, w=2.6, color="white")
    P.stroke([(61 + ox, 61 + oy), (86 + ox, 86 + oy)], w=8, color="brown")


@prop("detective_hat", "detective, investigator, private investigator, case closed, sleuth, inspector, noir, crime solver", "mystery")
def _(P):
    P.ellipse(50, 66, 42, 12, w=3.4, fill="brown")
    P.blob([(22, 64), (26, 36), (40, 26), (50, 30), (60, 26), (74, 36), (78, 64)], w=3.4, fill="brown")
    P.rect(24, 54, 76, 62, w=2.6, fill="black")
    P.curve([(40, 28), (50, 36), (60, 28)], w=2.2)
    P.stroke([(70, 84), (84, 90)], w=4)
    P.ellipse(64, 82, 7, 5, w=2.6, fill="brown")
    if int(P.t * 2) % 2:
        P.curve([(60, 76), (58, 68), (62, 62)], w=1.8, color="gray")


@prop("handcuffs", "arrest, arrested, police, crime, criminal, criminals, prison, jail, cuffs, handcuffs, caught, busted, charged", "mystery")
def _(P):
    sw = wave(P.t, 3, 4)
    P.circle(28, 58, 18, w=4.4, color="silver")
    P.circle(72 + sw * 0.2, 58, 18, w=4.4, color="silver")
    P.rect(40, 38, 46, 46, w=2.4, fill="silver")
    P.rect(54, 38, 60, 46, w=2.4, fill="silver")
    for i in range(3):
        P.ellipse(47 + i * 3, 38 - i * 2 + sw * 0.1, 3, 2, w=2)


@prop("police_badge", "police, cop, cops, officer, sheriff, law enforcement, fbi, detective badge, authorities, investigation team", "mystery")
def _(P):
    pts = []
    for i in range(14):
        a = math.radians(-90 + i * 360 / 14)
        r = 38 if i % 2 == 0 else 28
        pts.append((50 + r * math.cos(a), 52 + r * math.sin(a)))
    P.poly(pts, w=3.4, fill="gold")
    P.circle(50, 52, 16, w=2.6, fill="blue")
    P.star(50, 52, 9, 4, w=1.8, fill="gold")
    P.sparkle(80, 16, r=6, phase=0.4)


@prop("jail", "prison, jail, locked up, sentence, sentenced, inmate, prisoner, behind bars, cell, convicted, escape, escaped", "mystery")
def _(P):
    P.rect(14, 14, 86, 88, w=3.6, fill="gray")
    P.rect(14, 14, 86, 22, w=3, fill="black")
    for x in (26, 38, 50, 62, 74):
        P.line(x, 22, x, 88, w=4)
    P.line(14, 54, 86, 54, w=3)
    hx = 50 + wave(P.t, 1, 6)
    P.circle(hx, 70, 3, w=2, fill="skin")


@prop("gavel", "court, courts, judge, law, laws, legal, trial, verdict, lawsuit, sued, justice, ruling, lawyer, attorney, guilty", "mystery")
def _(P):
    sw = -30 + 30 * abs(math.sin(P.t * 3))
    head = rot([(26, 26), (58, 26), (58, 44), (26, 44)], 64, 64, sw)
    handle = rot([(40, 44), (84, 82)], 64, 64, sw)
    P.stroke(handle, w=6, color="brown")
    P.poly(head, w=3.4, fill="brown")
    P.rrect(54, 82, 90, 90, r=2, w=3, fill="brown")
    if sw > -6:
        P.line(50, 80, 44, 74, w=2.2, color="orange")
        P.line(92, 78, 96, 72, w=2.2, color="orange")


@prop("scales", "balance, justice, fair, unfair, compare, weigh, weighing, pros and cons, equality, judgement, equal, versus, vs", "mystery")
def _(P):
    a = wave(P.t, 1.6, 8)
    P.line(50, 14, 50, 82, w=3.6)
    P.rrect(34, 82, 66, 90, r=2, w=3, fill="gold")
    beam = rot([(16, 26), (84, 26)], 50, 26, a)
    P.stroke(beam, w=3.6)
    for (x, y), c in zip(beam, ("blue", "red")):
        P.line(x, y, x - 10, y + 26, w=1.8)
        P.line(x, y, x + 10, y + 26, w=1.8)
        P.arc(x, y + 26, 13, 7, 0, 180, w=3, color=c)
    P.circle(50, 14, 3.6, w=2, fill="gold")


@prop("map_x", "treasure, treasure map, map, buried, x marks the spot, hidden, hidden location, lost city, secret location, expedition", "mystery")
def _(P):
    P.poly([(12, 22), (34, 14), (60, 24), (88, 16), (88, 80), (60, 88), (34, 78), (12, 86)], w=3.4, fill="cream")
    P.line(34, 14, 34, 78, w=1.8)
    P.line(60, 24, 60, 88, w=1.8)
    P.stroke([(20, 74), (30, 64), (42, 66), (50, 52), (62, 50)], w=2.4, color="red")
    k = 1 + 0.15 * abs(math.sin(P.t * 4))
    P.line(66 - 6 * k, 38 - 6 * k, 66 + 6 * k, 38 + 6 * k, w=3.6, color="red")
    P.line(66 + 6 * k, 38 - 6 * k, 66 - 6 * k, 38 + 6 * k, w=3.6, color="red")


@prop("map_pin", "place, location, where, map pin, city, address, gps location, destination, spot, here, located, pinned", "mystery")
def _(P):
    hop = abs(math.sin(P.t * 3)) * 8
    P.ellipse(50, 88, 14, 4, w=2.2, fill="lightgray")
    P.poly([(50, 84 - hop), (28, 46 - hop), (30, 26 - hop), (42, 14 - hop), (58, 14 - hop), (70, 26 - hop), (72, 46 - hop)],
           w=3.6, fill="red", smooth=True)
    P.circle(50, 36 - hop, 9, w=2.6, fill="white")


@prop("compass", "direction, directions, explore, explorer, navigate, navigation, lost, adventure, north, south, east, west, journey", "mystery")
def _(P):
    P.circle(50, 50, 38, w=3.6, fill="cream")
    P.circle(50, 50, 31, w=2)
    P.text(50, 19, "N", size=9)
    a = wave(P.t, 2, 20) + wave(P.t, 5.3, 6)
    P.poly(rot([(50, 22), (57, 50), (43, 50)], 50, 50, a), w=2.4, fill="red")
    P.poly(rot([(50, 78), (57, 50), (43, 50)], 50, 50, a), w=2.4, fill="lightgray")
    P.dot(50, 50, 3)


@prop("question", "question, questions, why, unknown, mystery, unsolved, how, what, who, nobody knows, unexplained, puzzle, confused, "
      "what happened, theory, theories", "mystery")
def _(P):
    t = wave(P.t, 2, 6)
    pts = rot([(30, 30), (34, 16), (50, 10), (66, 16), (70, 30), (64, 42), (52, 50), (50, 64)], 50, 50, t)
    P.stroke(pts, w=8, color="purple", smooth=True)
    x, y = rot([(50, 82)], 50, 50, t)[0]
    P.circle(x, y, 5.6, w=2, fill="purple")


@prop("exclamation", "important, alert, surprise, shocking, wow, attention, warning sign, breaking, urgent, crazy, insane, fact", "mystery")
def _(P):
    k = 1 + 0.12 * abs(math.sin(P.t * 5))
    P.poly(scale([(42, 10), (58, 10), (54, 64), (46, 64)], 50, 40, k), w=3.4, fill="red")
    P.circle(50, 80, 7 * k, w=3, fill="red")


@prop("warning", "warning, danger, dangerous, caution, risk, risky, hazard, careful, beware, threat, unsafe, red flag", "mystery")
def _(P):
    on = int(P.t * 3) % 2 == 0 or P.t < 1
    P.poly([(50, 10), (90, 82), (10, 82)], w=4, fill="yellow" if on else "orange")
    P.poly([(46, 32), (54, 32), (52, 60), (48, 60)], w=2, fill="black")
    P.circle(50, 70, 4, w=1.6, fill="black")


@prop("check", "yes, correct, done, true, confirmed, fact check, verified, success, completed, right, approved, checklist, real", "mystery")
def _(P):
    P.circle(50, 50, 38, w=3.6, fill="green")
    P.stroke([(30, 52), (44, 66), (72, 34)], w=7, color="white")


@prop("cross", "no, wrong, false, myth, fake, fail, failed, cancel, cancelled, mistake, error, banned, not true, denied, hoax, lie", "mystery")
def _(P):
    sh = wave(P.t, 20, 2) if 0.8 < P.t < 1.3 else 0
    P.circle(50 + sh, 50, 38, w=3.6, fill="red")
    P.line(34 + sh, 34, 66 + sh, 66, w=7, color="white")
    P.line(66 + sh, 34, 34 + sh, 66, w=7, color="white")


@prop("lightbulb", "idea, ideas, invent, invention, inventor, smart, solution, tip, tips, eureka, innovation, genius, creative, "
      "bright idea, figured out, discovery, realize", "symbols")
def _(P):
    glow = 0.5 + 0.5 * math.sin(P.t * 5)
    P.poly([(50, 10), (70, 18), (78, 36), (70, 54), (62, 64), (38, 64), (30, 54), (22, 36), (30, 18)], w=3.6, fill="yellow", smooth=True)
    P.stroke([(42, 62), (44, 46), (50, 52), (56, 46), (58, 62)], w=2.2)
    P.rrect(38, 64, 62, 80, r=2, w=3, fill="gray")
    P.line(38, 70, 62, 70, w=2)
    P.line(38, 75, 62, 75, w=2)
    P.arc(50, 82, 6, 4, 0, 180, w=3)
    for a in (-150, -110, -70, -30, 10, 190):
        r = math.radians(a)
        r1, r2 = 36 + 2 * glow, 42 + 5 * glow
        P.line(50 + r1 * math.cos(r), 38 + r1 * math.sin(r), 50 + r2 * math.cos(r), 38 + r2 * math.sin(r), w=2.6, color="orange")


# ============================================================================================ COMMUNICATION / SCHOOL
@prop("book", "book, books, story, stories, read, reading, history, learn, learning, novel, library, education, knowledge, chapter, author", "school")
def _(P):
    flip = (P.t * 1.5) % 1
    P.poly([(50, 24), (14, 18), (14, 80), (50, 86)], w=3.4, fill="cream")
    P.poly([(50, 24), (86, 18), (86, 80), (50, 86)], w=3.4, fill="cream")
    for i in range(4):
        y = 32 + i * 10
        P.line(20, y, 44, y + 2, w=1.6)
        P.line(56, y + 2, 80, y, w=1.6)
    x = 50 + 36 * math.cos(math.pi * flip)
    P.stroke([(50, 24), (x, 20 + 6 * math.sin(math.pi * flip)), (x, 82 - 4 * math.sin(math.pi * flip)), (50, 86)], w=2.4)


@prop("scroll", "ancient, ancient times, history, historical, document, old document, legend, legends, myth, myths, decree, prophecy, "
      "manuscript, record, records, archive", "school")
def _(P):
    P.rect(22, 22, 78, 78, w=3, fill="cream")
    for i in range(5):
        P.curve([(30, 32 + i * 9), (45, 30 + i * 9), (60, 33 + i * 9), (70, 31 + i * 9)], w=1.8)
    for y in (18, 82):
        P.ellipse(50, y, 34, 6, w=3.2, fill="cream")
        P.circle(16, y, 4, w=2.4, fill="brown")
        P.circle(84, y, 4, w=2.4, fill="brown")
    P.circle(66, 70 + wave(P.t, 3, 1), 6, w=2.4, fill="red")


@prop("newspaper", "news, report, reports, reported, article, headline, headlines, press, journalist, newspaper, media, breaking news", "school")
def _(P):
    a = wave(P.t, 1.3, 3)
    P.poly(rot([(14, 16), (86, 16), (86, 86), (14, 86)], 50, 50, a), w=3.4, fill="paper")
    P.poly(rot([(20, 22), (80, 22), (80, 34), (20, 34)], 50, 50, a), w=2.2, fill="black")
    P.poly(rot([(20, 40), (46, 40), (46, 62), (20, 62)], 50, 50, a), w=2.2, fill="lightgray")
    for i in range(6):
        y = 42 + i * 7
        P.stroke(rot([(52, y), (80, y)], 50, 50, a), w=1.6)
    for i in range(2):
        y = 70 + i * 7
        P.stroke(rot([(20, y), (80, y)], 50, 50, a), w=1.6)


@prop("envelope", "email, emails, letter, letters, mail, message, messages, note, inbox, sent, newsletter, contact, invitation", "school")
def _(P):
    open_k = min(1, max(0, (P.t - 0.8) * 2))
    P.rect(12, 30, 88, 80, w=3.4, fill="cream")
    P.stroke([(12, 80), (42, 54)], w=2)
    P.stroke([(88, 80), (58, 54)], w=2)
    ty = 56 - 44 * open_k
    P.poly([(12, 30), (50, ty), (88, 30)], w=3, fill="cream")
    if open_k > 0.5:
        P.rect(26, 30 - 16 * open_k, 74, 44, w=2.4, fill="paper")
    P.circle(50, ty if open_k < 0.3 else 30, 4.5, w=2, fill="red")


@prop("speech_bubble", "talk, talking, say, said, says, quote, quotes, conversation, chat, comment, comments, told, words, rumor, rumors", "school")
def _(P):
    P.rrect(10, 16, 90, 66, r=18, w=3.4, fill="white")
    P.poly([(30, 64), (22, 86), (48, 65)], w=3.2, fill="white")
    for i in range(3):
        k = 1 if (int(P.t * 4) % 3) >= i or P.t < 0.8 else 0.3
        P.circle(32 + i * 18, 41, 5 * k, w=2, fill="ink")


@prop("thought_bubble", "think, thought, thoughts, imagine, imagination, dream, dreams, wonder, wondering, daydream, what if, believe", "school")
def _(P):
    P.blob([(20, 50), (14, 36), (24, 22), (40, 18), (52, 10), (68, 16), (82, 24), (88, 40), (80, 54), (64, 60), (46, 62), (30, 60)],
           w=3.4, fill="white")
    by = wave(P.t, 3, 2)
    P.circle(28, 72 + by, 6, w=2.8, fill="white")
    P.circle(18, 86 + by, 4, w=2.4, fill="white")
    P.text(52, 38, "...", size=20)


@prop("grad_cap", "school, college, university, graduate, graduation, student, students, degree, education, diploma, academic, study", "school")
def _(P):
    P.poly([(50, 18), (92, 36), (50, 54), (8, 36)], w=3.4, fill="black")
    P.poly([(26, 44), (26, 62), (50, 72), (74, 62), (74, 44), (50, 54)], w=3.2, fill="black")
    sw = wave(P.t, 3, 4)
    P.stroke([(50, 36), (80, 42), (82 + sw, 66)], w=2.4, color="yellow")
    P.rect(78 + sw, 66, 86 + sw, 76, w=2, fill="yellow")


@prop("pencil", "write, writing, wrote, draw, drawing, design, edit, note, notes, homework, sketch, plan, author, signed, signature", "school")
def _(P):
    a = -40 + wave(P.t, 4, 4)
    body = rot([(20, 42), (70, 42), (70, 58), (20, 58)], 50, 50, a)
    P.poly(body, w=3.4, fill="yellow")
    P.poly(rot([(70, 42), (86, 50), (70, 58)], 50, 50, a), w=3, fill="skin")
    P.poly(rot([(80, 47), (86, 50), (80, 53)], 50, 50, a), w=1.6, fill="black")
    P.poly(rot([(12, 42), (20, 42), (20, 58), (12, 58)], 50, 50, a), w=3, fill="pink")
    P.stroke(rot([(20, 50), (70, 50)], 50, 50, a), w=1.6)
    P.curve([(14, 88), (30, 82), (44, 88), (60, 84)], w=2.4, color="blue")


@prop("palette", "art, arts, paint, painting, painter, artist, creative, creativity, color, colors, colour, masterpiece, gallery", "school")
def _(P):
    P.blob([(20, 50), (24, 28), (44, 16), (68, 18), (86, 34), (88, 54), (76, 70), (60, 66), (52, 76), (40, 86), (24, 78)],
           w=3.4, fill="cream")
    P.circle(62, 52, 7, w=2.4, fill="paper")
    for (x, y), c in zip(((34, 34), (52, 26), (70, 32), (34, 56), (44, 72)), ("red", "yellow", "blue", "green", "purple")):
        P.blob([(x - 6, y), (x, y - 6), (x + 6, y), (x, y + 6)], w=1.8, fill=c)
    a = wave(P.t, 3, 6)
    P.stroke(rot([(70, 90), (90, 62)], 80, 76, a), w=4, color="brown")
    P.poly(rot([(88, 58), (94, 62), (90, 68), (86, 64)], 80, 76, a), w=2, fill="red")


@prop("music_note", "music, song, songs, melody, sing, singing, concert, band, musician, rap, album, hit song, beat, rhythm", "school")
def _(P):
    by = wave(P.t, 3, 4)
    P.ellipse(30, 74 + by, 12, 9, w=3, fill="black", rot=-20)
    P.ellipse(70, 64 - by, 12, 9, w=3, fill="black", rot=-20)
    P.line(41, 72 + by, 41, 22 + by, w=4)
    P.line(81, 62 - by, 81, 12 - by, w=4)
    P.poly([(41, 22 + by), (81, 12 - by), (81, 24 - by), (41, 34 + by)], w=3, fill="black")


@prop("bell", "bell, notification, notifications, ring, ringing, alert, reminder, ding, notify, alarm bell, subscribe, subscribers, subscribe bell", "school")
def _(P):
    a = 18 * math.sin(P.t * 9) * max(0, math.sin(P.t * 2)) if P.t > 0.6 else 0
    P.circle(*rot([(50, 14)], 50, 12, a)[0], 4, w=2.4, fill="gold")
    body = rot([(50, 16), (66, 24), (72, 46), (74, 66), (86, 74), (14, 74), (26, 66), (28, 46), (34, 24)], 50, 12, a)
    P.poly(body, w=3.6, fill="gold", smooth=True)
    P.circle(*rot([(50, 82)], 50, 12, a * 1.4)[0], 6, w=2.6, fill="gold")
    if abs(a) > 6:
        for s in (-1, 1):
            P.arc(50, 48, 46, 34, (-30 if s > 0 else 150), (10 if s > 0 else 190), w=2.4, color="orange")


# ============================================================================================ EVERYDAY OBJECTS
@prop("candle", "candle, candles, dark, darkness, seance, ritual, light, memorial, vigil, power outage, candlelight", "objects")
def _(P):
    f = 1 + 0.18 * math.sin(P.t * 11) + 0.08 * math.sin(P.t * 23)
    lean = wave(P.t, 4, 3)
    P.poly([(50, 40 - 22 * f), (58 + lean * 0.3, 34), (54, 44), (46, 44), (42 + lean * 0.3, 34)], w=2.4, fill="orange", smooth=True)
    P.poly([(50, 40 - 12 * f), (53, 38), (50, 44), (47, 38)], w=1.4, fill="yellow", smooth=True)
    P.line(50, 44, 50, 50, w=2.2)
    P.rect(38, 50, 62, 88, w=3.4, fill="cream")
    P.curve([(56, 50), (58, 58), (56, 62)], w=2.4, color="cream")
    P.ellipse(50, 90, 24, 5, w=3, fill="gray")


@prop("dice", "luck, lucky, chance, gamble, gambling, random, odds, casino, bet, betting, risk it, probability, coincidence", "objects")
def _(P):
    roll = int(P.t * 4) if P.t < 1.6 else 5
    a = -12 + (roll * 37) % 24
    P.poly(rot([(24, 24), (76, 24), (76, 76), (24, 76)], 50, 50, a), w=3.6, fill="white")
    pips = {0: [(50, 50)], 1: [(36, 36), (64, 64)], 2: [(36, 36), (50, 50), (64, 64)], 3: [(36, 36), (64, 36), (36, 64), (64, 64)],
            4: [(36, 36), (64, 36), (50, 50), (36, 64), (64, 64)], 5: [(36, 34), (64, 34), (36, 50), (64, 50), (36, 66), (64, 66)]}
    for x, y in pips[roll % 6]:
        P.dot(*rot([(x, y)], 50, 50, a)[0], 4.4, color="red" if roll % 6 == 0 else None)


@prop("puzzle", "puzzle, puzzles, solve, solved, piece, pieces, figure out, missing piece, put together, mystery solved, riddle, answer", "objects")
def _(P):
    def piece(ox, oy, c):
        pts = [(ox, oy), (ox + 14, oy), (ox + 14, oy - 7), (ox + 22, oy - 7), (ox + 22, oy), (ox + 36, oy), (ox + 36, oy + 14),
               (ox + 43, oy + 14), (ox + 43, oy + 22), (ox + 36, oy + 22), (ox + 36, oy + 36), (ox, oy + 36)]
        P.poly(pts, w=3.2, fill=c)
    piece(12, 30, "blue")
    k = min(1, max(0, (P.t - 0.6) * 1.4))
    piece(50 + 16 * (1 - k), 30 - 22 * (1 - k), "orange")


@prop("bomb", "bomb, explosion, explode, exploded, explosive, boom, blew up, viral hit, kaboom, blast, disaster, chaos", "objects")
def _(P):
    P.circle(44, 58, 30, w=3.6, fill="black")
    P.arc(44, 58, 22, 22, 200, 250, w=2.6, color="white")
    P.rect(52, 22, 64, 32, w=3, fill="gray")
    P.curve([(58, 22), (64, 12), (74, 12), (78, 6)], w=2.6, color="brown")
    k = 0.6 + 0.4 * abs(math.sin(P.t * 12))
    P.star(80, 6, 7 * k, 3 * k, n=6, w=1.8, fill="yellow")


@prop("balloon", "balloon, balloons, party, celebrate, celebration, float, floating, lighter than air, birthday party", "objects")
def _(P):
    for i, (x, c) in enumerate(((34, "red"), (62, "blue"))):
        by = wave(P.t, 2, 4, i * 2)
        bx = x + wave(P.t, 1.3, 3, i)
        P.ellipse(bx, 34 + by, 16, 20, w=3.2, fill=c)
        P.poly([(bx - 3, 54 + by), (bx + 3, 54 + by), (bx, 58 + by)], w=2, fill=c)
        P.curve([(bx, 58 + by), (bx - 4, 70), (bx + 4, 80), (50, 92)], w=1.8)


@prop("party_popper", "party, celebrate, celebration, congrats, congratulations, new year, festival, cheers, hooray, achievement unlocked", "objects")
def _(P):
    P.poly([(14, 88), (40, 40), (60, 60)], w=3.4, fill="purple")
    P.line(26, 70, 44, 72, w=2, color="yellow")
    P.line(22, 78, 34, 82, w=2, color="yellow")
    for i in range(10):
        a = math.radians(-80 + i * 9)
        d = 10 + ((P.t * 40 + i * 7) % 40)
        x, y = 52 + d * math.cos(a), 50 + d * math.sin(a)
        c = ("red", "yellow", "blue", "green", "pink")[i % 5]
        if i % 2:
            P.rect(x - 2, y - 2, x + 2, y + 2, w=1.4, fill=c)
        else:
            P.curve([(x - 3, y), (x, y - 3), (x + 3, y)], w=2, color=c)


@prop("flag", "flag, flags, country, countries, nation, national, patriot, finish line, start, conquer, claim, territory, independence", "objects")
def _(P):
    P.line(22, 10, 22, 92, w=4)
    pts = [(22, 14)]
    for i in range(1, 9):
        x = 22 + i * 7.5
        pts.append((x, 14 + wave(P.t, 6, 4, -i * 0.6)))
    for i in range(8, -1, -1):
        x = 22 + i * 7.5
        pts.append((x, 50 + wave(P.t, 6, 4, -i * 0.6)))
    P.poly(pts, w=3.2, fill="red")
    P.circle(22, 9, 3.4, w=2, fill="gold")


@prop("shield", "protect, protection, security, defense, defence, safe, safety, insurance, guard, shielded, immune, immunity, defend", "objects")
def _(P):
    P.poly([(50, 10), (84, 22), (82, 52), (66, 76), (50, 90), (34, 76), (18, 52), (16, 22)], w=3.8, fill="blue", smooth=True)
    P.poly([(50, 20), (74, 28), (72, 52), (50, 78)], w=0.1, fill="lightblue")
    P.stroke([(36, 50), (46, 60), (66, 38)], w=5, color="white")
    P.sparkle(80, 14, r=6, phase=0.2)


@prop("sword", "battle, war, wars, fight, fighting, knight, knights, warrior, combat, conflict, medieval, army, soldiers, duel", "objects")
def _(P):
    a = 45 + wave(P.t, 2, 4)
    P.poly(rot([(46, 6), (54, 6), (54, 62), (50, 70), (46, 62)], 50, 50, a), w=3.2, fill="silver")
    P.poly(rot([(32, 66), (68, 66), (68, 72), (32, 72)], 50, 50, a), w=3, fill="gold")
    P.poly(rot([(46, 72), (54, 72), (54, 88), (46, 88)], 50, 50, a), w=3, fill="brown")
    P.circle(*rot([(50, 92)], 50, 50, a)[0], 4, w=2.4, fill="gold")


@prop("umbrella", "umbrella, rain cover, insurance cover, protected from rain, rainy day, cover, shelter", "objects")
def _(P):
    a = wave(P.t, 1.8, 5)
    canopy = rot([(10, 50), (16, 30), (32, 16), (50, 12), (68, 16), (84, 30), (90, 50), (76, 44), (64, 50), (50, 44), (36, 50),
                  (24, 44)], 50, 50, a)
    P.poly(canopy, w=3.4, fill="red", smooth=True)
    P.stroke(rot([(50, 12), (50, 82)], 50, 50, a), w=3.2)
    P.arc(*rot([(43, 82)], 50, 50, a)[0], 7, 7, 0, 180, w=3.2)
    for i in range(4):
        x = 14 + i * 24
        y = (P.t * 60 + i * 20) % 30 + 60
        P.line(x, y, x - 2, y + 6, w=1.8, color="blue")


@prop("anchor", "anchor, stable, stability, sailor, sailors, navy, harbor, harbour, stuck, grounded, hold on", "objects")
def _(P):
    a = wave(P.t, 1.6, 6)
    P.circle(*rot([(50, 16)], 50, 16, a)[0], 7, w=3.2)
    P.stroke(rot([(50, 23), (50, 84)], 50, 16, a), w=4.4)
    P.stroke(rot([(34, 34), (66, 34)], 50, 16, a), w=4)
    P.stroke(rot([(18, 60), (24, 74), (38, 84), (50, 86), (62, 84), (76, 74), (82, 60)], 50, 16, a), w=4.4, smooth=True)
    P.poly(rot([(14, 62), (22, 56), (24, 66)], 50, 16, a), w=2.4, fill="ink")
    P.poly(rot([(86, 62), (78, 56), (76, 66)], 50, 16, a), w=2.4, fill="ink")


@prop("tools", "build, building, repair, fix, fixed, tools, diy, construction, renovate, maintenance, engineer, engineering, mechanic", "objects")
def _(P):
    a = wave(P.t, 3, 10)
    P.poly(rot([(18, 76), (24, 82), (70, 36), (64, 30)], 50, 50, -a * 0.4), w=3, fill="silver")
    P.poly(rot([(58, 18), (72, 14), (86, 28), (82, 42), (72, 34), (66, 38), (62, 32), (66, 28)], 50, 50, -a * 0.4), w=3, fill="silver")
    P.poly(rot([(74, 84), (80, 78), (34, 32), (28, 38)], 50, 50, a), w=3, fill="brown")
    P.poly(rot([(14, 30), (30, 14), (44, 28), (28, 44)], 50, 50, a), w=3.2, fill="gray")


@prop("shovel", "dig, digging, buried, bury, excavate, excavation, grave digging, unearthed, archaeology, archaeologist, found underground", "objects")
def _(P):
    a = wave(P.t, 3, 8)
    P.stroke(rot([(30, 14), (62, 66)], 50, 50, a), w=4.4, color="brown")
    P.stroke(rot([(22, 18), (38, 8)], 50, 50, a), w=4.4, color="brown")
    P.poly(rot([(56, 60), (70, 52), (84, 76), (74, 90), (62, 84)], 50, 50, a), w=3.2, fill="silver")
    P.blob([(10, 90), (24, 80), (40, 86), (34, 94), (14, 94)], w=2.6, fill="brown")


@prop("ladder", "climb, climbing, career ladder, steps to success, progress, level up, rise to the top, promotion", "objects")
def _(P):
    P.line(28, 10, 34, 92, w=4)
    P.line(72, 10, 66, 92, w=4)
    for i in range(6):
        y = 18 + i * 13
        P.line(29 + i * 0.8, y, 71 - i * 0.8, y, w=3.2)
    k = (P.t * 0.5) % 1
    P.circle(50, 84 - k * 70, 4, w=2, fill="red")


@prop("infinity", "forever, infinite, infinity, endless, never ending, eternal, unlimited, loop, always, eternity", "symbols")
def _(P):
    pts = [(50 + 36 * math.cos(a) / (1 + math.sin(a) ** 2), 50 + 36 * math.sin(a) * math.cos(a) / (1 + math.sin(a) ** 2))
           for a in [i / 60 * 2 * math.pi for i in range(61)]]
    P.stroke(pts, w=6, color="purple")
    a = P.t * 2.4
    P.dot(50 + 36 * math.cos(a) / (1 + math.sin(a) ** 2), 50 + 36 * math.sin(a) * math.cos(a) / (1 + math.sin(a) ** 2), 4.4,
          color="yellow")


@prop("recycle", "recycle, recycling, reuse, environment, environmental, cycle, sustainability, sustainable, green planet, waste", "symbols")
def _(P):
    a0 = P.t * 30
    for k in range(3):
        a = a0 + k * 120
        p1 = rot([(50, 18)], 50, 52, a)[0]
        p2 = rot([(78, 62)], 50, 52, a)[0]
        P.arrow(p1[0], p1[1], p2[0] - (p2[0] - p1[0]) * 0.18, p2[1] - (p2[1] - p1[1]) * 0.18, w=5, head=10, color="green")


@prop("cycle", "repeat, repeated, cycle, again, over and over, loop, refresh, restart, reset, comeback, history repeats", "symbols")
def _(P):
    a = P.t * 90
    for base in (0, 180):
        arc = [(50 + 32 * math.cos(math.radians(base + x)), 50 + 32 * math.sin(math.radians(base + x))) for x in range(10, 151, 10)]
        arc = rot(arc, 50, 50, a)
        P.stroke(arc, w=6, color="blue")
        (x1, y1), (x2, y2) = arc[-2], arc[-1]
        ang = math.atan2(y2 - y1, x2 - x1)
        tip = (x2 + 9 * math.cos(ang), y2 + 9 * math.sin(ang))
        P.poly([tip, (x2 + 9 * math.cos(ang + 2.2), y2 + 9 * math.sin(ang + 2.2)),
                (x2 + 9 * math.cos(ang - 2.2), y2 + 9 * math.sin(ang - 2.2))], w=2.6, fill="blue")


@prop("arrow_up", "up, increase, increasing, more, higher, rise, raised, upgrade, top, going up, improvement, better", "symbols")
def _(P):
    b = wave(P.t, 4, 4)
    P.poly([(50, 8 + b), (84, 44 + b), (64, 44 + b), (64, 90 + b), (36, 90 + b), (36, 44 + b), (16, 44 + b)], w=3.6, fill="green")


@prop("arrow_down", "down, decrease, decreasing, less, lower, fall, fell, dropped, downgrade, worse, decline", "symbols")
def _(P):
    b = wave(P.t, 4, 4)
    P.poly([(50, 92 + b), (84, 56 + b), (64, 56 + b), (64, 10 + b), (36, 10 + b), (36, 56 + b), (16, 56 + b)], w=3.6, fill="red")


@prop("glasses", "smart, nerd, nerdy, read, glasses, see clearly, clarity, intellectual, geek, focus, perspective", "objects")
def _(P):
    by = wave(P.t, 2, 2)
    for x in (30, 70):
        P.circle(x, 52 + by, 18, w=4, fill="lightblue")
        P.arc(x, 52 + by, 11, 11, 200, 250, w=2.2, color="white")
    P.arc(50, 50 + by, 6, 5, 200, 340, w=3.4)
    P.line(12, 48 + by, 4, 40 + by, w=3.4)
    P.line(88, 48 + by, 96, 40 + by, w=3.4)


@prop("top_hat", "magic, magician, trick, tricks, illusion, illusionist, gentleman, classy, fancy, formal, show", "objects")
def _(P):
    P.ellipse(50, 78, 40, 9, w=3.4, fill="black")
    P.poly([(28, 78), (30, 22), (70, 22), (72, 78)], w=3.4, fill="black")
    P.ellipse(50, 22, 20, 5, w=3, fill="black")
    P.rect(29, 62, 71, 70, w=2.4, fill="red")
    hop = max(0, math.sin(P.t * 2.5)) * 14 if P.t > 0.8 else 0
    if hop > 2:
        P.ellipse(44, 22 - hop, 4, 9, w=2.2, fill="white")
        P.ellipse(56, 22 - hop, 4, 9, w=2.2, fill="white")


@prop("magic_wand", "magic, magical, sparkle, amazing, special, new, shiny, wish, wishes, spell, fantasy, miracle, transform", "objects")
def _(P):
    a = wave(P.t, 4, 10)
    P.poly(rot([(18, 80), (24, 86), (66, 44), (60, 38)], 63, 41, a), w=3, fill="black")
    P.poly(rot([(58, 40), (64, 46), (68, 42), (62, 36)], 63, 41, a), w=2, fill="white")
    P.star(*rot([(70, 30)], 63, 41, a)[0], 12, 5, w=2.6, fill="yellow")
    P.sparkle(84, 16, r=6, phase=0)
    P.sparkle(56, 12, r=4, phase=1.5)
    P.sparkle(86, 46, r=4, phase=3)


@prop("ring", "wedding, marriage, married, engagement, engaged, proposal, propose, husband, wife, bride, groom, spouse", "objects")
def _(P):
    P.ellipse(50, 62, 26, 24, w=5, color="gold")
    P.poly([(38, 34), (62, 34), (68, 26), (50, 12), (32, 26)], w=3, fill="lightblue")
    P.stroke([(32, 26), (68, 26)], w=1.8)
    P.sparkle(74, 14, r=7, phase=0.5)
    P.sparkle(26, 16, r=4, phase=2)


@prop("bed", "sleep, sleeping, slept, tired, rest, dream, insomnia, bedtime, nap, exhausted, asleep, bedroom", "objects")
def _(P):
    P.rect(10, 52, 90, 70, w=3.4, fill="blue")
    P.rect(10, 34, 18, 82, w=3, fill="brown")
    P.rect(82, 46, 90, 82, w=3, fill="brown")
    P.rrect(20, 42, 40, 54, r=5, w=2.6, fill="white")
    for i in range(3):
        k = (P.t * 0.8 + i / 3) % 1
        P.text(48 + i * 9 + k * 6, 30 - i * 8 - k * 10, "Z", size=8 + i * 3, color="purple")


@prop("trash", "trash, garbage, rubbish, waste, delete, deleted, bin, throw away, junk, landfill, worthless", "objects")
def _(P):
    lid = max(0, math.sin(P.t * 3)) * 10 if P.t > 0.8 else 0
    P.poly(rot([(18, 24), (82, 24), (82, 30), (18, 30)], 82, 30, -lid), w=3.2, fill="gray")
    P.rect(42, 16 - lid * 0.2, 58, 24, w=2.6)
    P.poly([(24, 32), (76, 32), (70, 90), (30, 90)], w=3.4, fill="gray")
    for x in (40, 50, 60):
        P.line(x, 42, x - (x - 50) * 0.1, 80, w=2.2)


@prop("box", "package, packages, delivery, deliver, delivered, shipping, shipped, box, mystery box, order, ordered, parcel, moving house", "objects")
def _(P):
    open_k = max(0, math.sin(P.t * 2)) if P.t > 0.8 else 0
    P.poly([(14, 40), (50, 54), (50, 92), (14, 78)], w=3.4, fill="brown")
    P.poly([(86, 40), (50, 54), (50, 92), (86, 78)], w=3.4, fill="brown")
    P.poly([(14, 40), (50, 26), (86, 40), (50, 54)], w=3, fill="cream" if open_k > 0.2 else "brown")
    if open_k > 0.2:
        P.poly([(14, 40), (4, 30 - 6 * open_k), (40, 16 - 4 * open_k), (50, 26)], w=2.6, fill="brown")
        P.sparkle(50, 22 - 10 * open_k, r=7, phase=0)
    P.line(26, 70, 40, 76, w=2)


@prop("backpack", "travel, backpack, backpacking, school bag, adventure, hiking, explorer gear, trip, wanderlust", "objects")
def _(P):
    by = wave(P.t, 3, 1.5)
    P.arc(50, 24 + by, 12, 10, 180, 360, w=3.4)
    P.rrect(22, 22 + by, 78, 90 + by, r=16, w=3.6, fill="orange")
    P.rrect(30, 56 + by, 70, 82 + by, r=6, w=3, fill="orange")
    P.line(30, 64 + by, 70, 64 + by, w=2.2)
    P.rect(46, 60 + by, 54, 68 + by, w=2, fill="gold")


@prop("suitcase", "vacation, holiday, trip, luggage, travelling, traveling, moving, airport, packing, tourist, tourism, abroad", "objects")
def _(P):
    roll = wave(P.t, 3, 2)
    P.rrect(38, 12, 62, 24, r=4, w=3.2)
    P.rrect(18, 22, 82, 84, r=8, w=3.6, fill="teal")
    for x in (34, 66):
        P.line(x, 22, x, 84, w=2.4)
    P.rect(24, 36, 40, 46, w=2, fill="yellow")
    P.circle(30 + roll, 90, 4, w=2.4)
    P.circle(70 + roll, 90, 4, w=2.4)


@prop("ticket", "ticket, tickets, concert, event, events, lottery, admission, show, raffle, jackpot, entry, pass", "objects")
def _(P):
    a = wave(P.t, 2, 6)
    pts = [(12, 30), (88, 30), (88, 44), (82, 50), (88, 56), (88, 70), (12, 70), (12, 56), (18, 50), (12, 44)]
    P.poly(rot(pts, 50, 50, a), w=3.4, fill="yellow")
    for y in range(34, 68, 6):
        P.stroke(rot([(66, y), (66, y + 3)], 50, 50, a), w=1.6)
    P.star(*rot([(38, 50)], 50, 50, a)[0], 9, 4, w=2, fill="red")


@prop("telephone", "call, called, calling, phone call, ring ring, contact, hotline, landline, old phone, prank call, 911", "objects")
def _(P):
    sh = wave(P.t, 30, 2) if (int(P.t * 2) % 2 == 0 and P.t > 0.8) else 0
    P.poly([(18 + sh, 46), (82 + sh, 46), (90 + sh, 86), (10 + sh, 86)], w=3.4, fill="red")
    P.circle(50 + sh, 66, 11, w=2.6, fill="white")
    for i in range(8):
        a = math.radians(i * 40 - 90)
        P.dot(50 + sh + 7 * math.cos(a), 66 + 7 * math.sin(a), 1.4)
    P.poly([(14 + sh, 34), (30 + sh, 24), (70 + sh, 24), (86 + sh, 34), (78 + sh, 42), (68 + sh, 34), (32 + sh, 34),
            (22 + sh, 42)], w=3.2, fill="red")
    if sh:
        P.line(6, 22, 0, 16, w=2.4, color="orange")
        P.line(94, 22, 100, 16, w=2.4, color="orange")


@prop("radio", "radio, broadcast, signal, transmission, morse code, frequency, station, radio waves, last transmission, mayday", "objects")
def _(P):
    P.line(70, 30, 82, 6, w=2.6)
    P.rrect(12, 30, 88, 84, r=8, w=3.6, fill="brown")
    P.circle(34, 58, 14, w=3, fill="lightgray")
    for r in (4, 8, 12):
        P.circle(34, 58, r, w=1.4)
    P.rect(56, 42, 80, 52, w=2.4, fill="cream")
    P.line(60 + ((P.t * 12) % 16), 42, 60 + ((P.t * 12) % 16), 52, w=2, color="red")
    P.circle(62, 70, 5, w=2.2, fill="gray")
    P.circle(76, 70, 5, w=2.2, fill="gray")
    k = (P.t * 1.5) % 1
    for i in range(2):
        r = 6 + i * 6 + k * 6
        P.arc(82, 6, r, r, -60, 20, w=1.8, color="teal")


@prop("sos", "sos, help, rescue, rescued, emergency, distress, stranded, mayday, call for help, survivor, survivors, signal for help", "objects")
def _(P):
    on = int(P.t * 3) % 2 == 0 or P.t < 1
    P.rrect(8, 26, 92, 74, r=10, w=3.6, fill="red" if on else "orange")
    P.text(50, 50, "SOS", size=30, color="white")


@prop("paper_plane", "send, sent, sending, message sent, launch, deliver, fly away, idea takes off, submit, shipped it", "objects")
def _(P):
    x = wave(P.t, 1.5, 6)
    y = wave(P.t, 2.3, 5)
    P.curve([(8, 86), (20, 72), (14, 62), (30, 58)], w=2, color="gray")
    P.poly([(18 + x, 52 + y), (88 + x, 18 + y), (50 + x, 80 + y), (44 + x, 60 + y)], w=3.2, fill="white")
    P.stroke([(44 + x, 60 + y), (88 + x, 18 + y)], w=2.2)
    P.poly([(44 + x, 60 + y), (40 + x, 76 + y), (50 + x, 66 + y)], w=2.4, fill="lightgray")


@prop("door", "door, doors, entrance, exit, open door, opportunity, portal, secret room, room, enter, entered, locked room, inside", "objects")
def _(P):
    P.rect(20, 10, 80, 92, w=3.6, fill="black")
    k = min(1, max(0, (P.t - 0.6) * 1.2)) * 0.55
    P.poly([(24, 14), (24 + 52 * (1 - k), 14 + 6 * k), (24 + 52 * (1 - k), 88 - 6 * k), (24, 88)], w=3.2, fill="brown")
    P.circle(24 + 52 * (1 - k) - 7, 52, 3, w=2, fill="gold")
    if k > 0.2:
        P.sparkle(66, 50, r=8, color="yellow", phase=0)


@prop("tombstone", "grave, graves, cemetery, graveyard, rip, rest in peace, buried, funeral, died, death, tomb, memorial, passed away", "objects")
def _(P):
    P.poly([(24, 88), (24, 38), (34, 20), (50, 14), (66, 20), (76, 38), (76, 88)], w=3.6, fill="gray", smooth=True)
    P.text(50, 48, "RIP", size=15)
    P.line(36, 64, 64, 64, w=1.8)
    P.line(40, 72, 60, 72, w=1.8)
    P.curve([(8, 90), (30, 86), (70, 88), (92, 86)], w=3, color="green")
    f = wave(P.t, 2, 3)
    if P.t > 1:
        P.blob([(86 + f, 30), (82 + f, 22), (86 + f, 14), (90 + f, 22)], w=1.6, fill="white")
