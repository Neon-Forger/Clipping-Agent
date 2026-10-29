"""Prop library part 1: tech, AI, science, space, money, business, time.
Every drawing is in a 0-100 box (y goes down). P is a sketch.Pen; P.t is seconds since the prop appeared."""
import math

from .props import prop, rot, wave


# =============================================================================================== TECH / AI
@prop("ai_chat", "ai, artificial intelligence, chatbot, chat bot, chatgpt, claude, claude ai, gemini, copilot, assistant, "
      "ai assistant, llm, language model, openai, anthropic, ai model, ai tool, prompt, grok, deepseek, ai app", "tech")
def _(P):
    P.rrect(10, 14, 90, 70, r=16, w=3.4, fill="lightblue")
    P.poly([(26, 68), (18, 88), (44, 69)], w=3.2, fill="lightblue")
    s = 1 + 0.08 * math.sin(P.t * 4)
    P.star(50, 42, 17 * s, 5, n=4, w=2.8, fill="yellow")
    P.star(71, 27, 6, 2, n=4, w=2.0, fill="yellow", rot=-90 + P.t * 40)
    P.star(31, 55, 4.5, 1.6, n=4, w=1.8, fill="yellow")


@prop("robot", "robot, android, bot, machine, automation, automated, robotics, cyborg", "tech")
def _(P):
    P.line(50, 22, 50, 9, w=3)
    P.circle(50, 7, 4, w=2.5, fill="red" if int(P.t * 2) % 2 == 0 else "yellow")
    P.rect(18, 35, 24, 50, w=2.8, fill="gray")
    P.rect(76, 35, 82, 50, w=2.8, fill="gray")
    P.rrect(24, 22, 76, 64, r=9, w=3.4, fill="silver")
    blink = (int(P.t * 12) % 30) < 2
    for x in (38, 62):
        if blink:
            P.line(x - 6, 40, x + 6, 40, w=3)
        else:
            P.circle(x, 40, 7, w=2.8, fill="lightblue")
            P.dot(x + 1.5, 40, 2.4)
    P.rrect(36, 50, 64, 58, r=2, w=2.5)
    for x in (43, 50, 57):
        P.line(x, 50.5, x, 57.5, w=1.8)
    P.rrect(32, 66, 68, 92, r=6, w=3.2, fill="silver")
    P.circle(50, 78, 5, w=2.4, fill="red")


@prop("brain", "brain, mind, think, thinking, smart, intelligence, memory, psychology, iq, genius, neuroscience, mental", "tech")
def _(P):
    P.blob([(20, 50), (18, 35), (28, 22), (44, 17), (56, 16), (72, 20), (83, 32), (84, 48), (78, 62), (64, 70), (50, 71),
            (35, 70), (24, 62)], w=3.4, fill="pink")
    P.curve([(51, 19), (48, 32), (53, 45), (49, 58), (51, 70)], w=2.6)
    for pts in ([(28, 36), (35, 30), (41, 37)], [(26, 50), (34, 45), (40, 54)], [(33, 62), (41, 58), (44, 64)],
                [(60, 30), (66, 36), (73, 31)], [(59, 48), (67, 44), (75, 51)], [(58, 61), (65, 57), (71, 63)]):
        P.curve(pts, w=2.2)
    P.stroke([(55, 71), (58, 84)], w=3.2)
    k = abs(math.sin(P.t * 3))
    P.stroke([(84, 22), (90 + 3 * k, 16 - 3 * k)], w=2.2, color="yellow")
    P.stroke([(16, 22), (10 - 3 * k, 16 - 3 * k)], w=2.2, color="yellow")


@prop("chip", "chip, processor, cpu, gpu, nvidia, semiconductor, hardware, microchip, computer chip, transistor", "tech")
def _(P):
    for i in range(4):
        y = 33 + i * 11
        P.line(14, y, 25, y, w=2.6)
        P.line(75, y, 86, y, w=2.6)
        P.line(y, 14, y, 25, w=2.6)
        P.line(y, 75, y, 86, w=2.6)
    P.rrect(25, 25, 75, 75, r=5, w=3.4, fill="gray")
    P.rrect(36, 36, 64, 64, r=3, w=2.6, fill="lightgray")
    k = 0.5 + 0.5 * math.sin(P.t * 5)
    P.dot(50, 50, 3 + 2 * k, color="teal")


@prop("laptop", "laptop, computer, pc, macbook, notebook computer, work from home, remote work, desktop, coding on laptop", "tech")
def _(P):
    P.rrect(18, 16, 82, 62, r=4, w=3.2, fill="gray")
    P.rect(23, 21, 77, 57, w=2.4, fill="lightblue")
    n = int(P.t * 6) % 6
    for i in range(4):
        ln = [22, 34, 16, 28][(i + n) % 4]
        P.line(28, 28 + i * 7, 28 + ln, 28 + i * 7, w=2.2)
    P.poly([(8, 66), (92, 66), (85, 75), (15, 75)], w=3.2, fill="silver")
    P.line(42, 70, 58, 70, w=2)


@prop("phone", "phone, smartphone, iphone, android phone, mobile, cell phone, app, text message, texting, screen time, scrolling", "tech")
def _(P):
    P.rrect(30, 8, 70, 92, r=9, w=3.4, fill="black")
    P.rrect(34, 16, 66, 80, r=3, w=2.2, fill="lightblue")
    P.line(45, 12, 55, 12, w=2, color="silver")
    P.circle(50, 86, 2.6, w=1.8, color="silver")
    for i, c in enumerate(("red", "yellow", "green", "purple", "orange", "teal")):
        x, y = 39 + (i % 3) * 9, 24 + (i // 3) * 10
        P.rrect(x - 3, y - 3, x + 3, y + 3, r=1.5, w=1.4, fill=c)
    if P.t > 0.9:
        k = min(1, (P.t - 0.9) * 4)
        P.circle(67, 12, 6 * k, w=2, fill="red")
        P.text(67, 12, "1", size=7 * k, color="white")


@prop("code", "code, coding, programming, software, developer, programmer, script, html, python, javascript, hacker, hack", "tech")
def _(P):
    P.rrect(10, 16, 90, 84, r=6, w=3.2, fill="cream")
    P.line(10, 27, 90, 27, w=2.4)
    for i, c in enumerate(("red", "yellow", "green")):
        P.dot(17 + i * 6, 21.5, 1.8, color=c)
    P.stroke([(36, 42), (24, 55), (36, 68)], w=3.6, color="blue")
    P.stroke([(64, 42), (76, 55), (64, 68)], w=3.6, color="blue")
    P.line(56, 38, 44, 72, w=3.4, color="purple")
    if int(P.t * 2) % 2 == 0:
        P.line(80, 74, 86, 74, w=2.4)


@prop("wifi", "wifi, wi-fi, internet, online, signal, wireless, connection, network, connected, broadband, hotspot", "tech")
def _(P):
    n = int(P.t * 3) % 4
    P.dot(50, 78, 5, color="blue")
    for i, r in enumerate((16, 30, 44)):
        P.arc(50, 80, r, r, 225, 315, w=6 if i == n - 1 else 4.4, color="blue" if i < n or P.t < 0.8 else "lightblue")


@prop("cloud", "cloud, cloud storage, storage, upload, server, servers, data, data center, backup, icloud, the cloud", "tech")
def _(P):
    P.blob([(18, 66), (14, 54), (22, 42), (33, 40), (38, 27), (52, 22), (65, 28), (70, 40), (82, 42), (88, 55), (84, 66)],
           w=3.4, fill="lightblue")
    dy = wave(P.t, 4, 2)
    P.arrow(50, 62 + dy, 50, 38 + dy, w=3.6, head=8)


@prop("gear", "gear, gears, settings, engine, mechanism, process, system, machinery, cog, mechanical, industry, how it works", "tech")
def _(P):
    a0 = P.t * 40
    pts = []
    for i in range(40):
        a = math.radians(a0 + i * 9)
        r = 36 if (i // 2) % 2 == 0 else 28
        pts.append((50 + r * math.cos(a), 50 + r * math.sin(a)))
    P.poly(pts, w=3.2, fill="gray")
    P.circle(50, 50, 11, w=3, fill="paper")


@prop("lock", "lock, locked, security, password, privacy, safe, secure, protected, padlock, encryption, encrypted", "tech")
def _(P):
    P.arc(50, 42, 17, 22, 180, 360, w=5)
    P.line(33, 42, 33, 46, w=5)
    P.line(67, 42, 67, 46, w=5)
    P.rrect(24, 44, 76, 86, r=7, w=3.4, fill="gold")
    P.circle(50, 60, 5, w=2.6, fill="ink")
    P.line(50, 63, 50, 74, w=4)


@prop("key", "key, keys, unlock, unlocked, access, secret, answer, the key, solution, keyhole", "tech")
def _(P):
    pts = rot([(46, 50), (88, 50)], 50, 50, wave(P.t, 2, 4))
    P.circle(30, 50, 15, w=3.4, fill="gold")
    P.circle(30, 50, 5, w=2.6, fill="paper")
    P.stroke(pts, w=4.4)
    P.stroke([(76, 50), (76, 61)], w=4)
    P.stroke([(84, 50), (84, 58)], w=4)


@prop("bug", "bug, glitch, error, virus, insect, beetle, computer virus, malware, crash", "tech")
def _(P):
    wig = wave(P.t, 10, 2.5)
    for s in (-1, 1):
        for i, y in enumerate((48, 58, 68)):
            P.stroke([(50 + s * 14, y), (50 + s * 26, y - 4 + (wig if i % 2 else -wig)), (50 + s * 32, y + 4)], w=2.6)
        P.stroke([(50 + s * 4, 26), (50 + s * 12, 14)], w=2.4)
    P.ellipse(50, 58, 17, 23, w=3.4, fill="red")
    P.line(50, 37, 50, 80, w=2.4)
    P.circle(50, 31, 8, w=3, fill="black")
    for x, y in ((42, 52), (58, 52), (44, 66), (57, 68)):
        P.dot(x, y, 2.6)


@prop("battery", "battery, charge, charging, power, energy, battery life, low battery, recharge, electric", "tech")
def _(P):
    P.rrect(16, 32, 80, 68, r=6, w=3.4)
    P.rect(80, 42, 87, 58, w=3, fill="ink")
    lvl = 0.25 + 0.7 * ((P.t * 0.5) % 1)
    col = "green" if lvl > 0.5 else ("yellow" if lvl > 0.3 else "red")
    P.rect(21, 37, 21 + 54 * lvl, 63, w=1.6, fill=col)
    P.poly([(52, 36), (40, 52), (50, 52), (46, 64), (60, 46), (50, 46)], w=2.2, fill="yellow")


@prop("satellite", "satellite, gps, orbit, space station, signal from space, starlink, communications", "tech")
def _(P):
    a = wave(P.t, 0.8, 6)
    body = rot([(42, 42), (58, 42), (58, 58), (42, 58)], 50, 50, a)
    P.poly(body, w=3.2, fill="silver")
    for s in (-1, 1):
        panel = rot([(50 + s * 10, 44), (50 + s * 38, 44), (50 + s * 38, 56), (50 + s * 10, 56)], 50, 50, a)
        P.poly(panel, w=2.8, fill="blue")
        for k in (0.33, 0.66):
            x = 50 + s * (10 + 28 * k)
            P.stroke(rot([(x, 44), (x, 56)], 50, 50, a), w=1.6)
    P.stroke(rot([(50, 42), (50, 32)], 50, 50, a), w=2.4)
    P.arc(*rot([(50, 30)], 50, 50, a)[0], 7, 4, 180, 360, w=2.6)
    for i in range(3):
        r = 8 + ((P.t * 14 + i * 7) % 21)
        P.arc(50, 30, r, r, 230, 310, w=1.8, color="teal")


@prop("camera", "camera, photo, photograph, picture, photography, filming, cctv, security camera, snapshot, selfie", "tech")
def _(P):
    P.rect(28, 22, 46, 32, w=2.8, fill="gray")
    P.rrect(14, 30, 86, 78, r=7, w=3.4, fill="gray")
    P.circle(50, 55, 18, w=3.2, fill="black")
    P.circle(50, 55, 10, w=2.6, fill="lightblue")
    P.dot(46, 51, 2.4, color="white")
    flash = int(P.t * 1.5) % 3 == 0 and P.t > 0.8
    P.rect(70, 36, 79, 42, w=2.2, fill="yellow" if flash else "lightgray")
    if flash:
        for a in range(0, 360, 60):
            r = math.radians(a)
            P.stroke([(74.5 + 8 * math.cos(r), 39 + 8 * math.sin(r)), (74.5 + 13 * math.cos(r), 39 + 13 * math.sin(r))],
                     w=1.8, color="yellow")


@prop("clapper", "movie, movies, film, films, cinema, director, hollywood, scene, take, action, actor, actress, filmmaking", "tech")
def _(P):
    P.rect(16, 44, 84, 86, w=3.4, fill="gray")
    P.line(16, 58, 84, 58, w=2.2)
    open_a = -14 - 12 * max(0, math.sin(P.t * 4))
    top = rot([(16, 32), (84, 32), (84, 44), (16, 44)], 16, 44, open_a)
    P.poly(top, w=3.2, fill="black")
    for i in range(4):
        x = 24 + i * 16
        P.stroke(rot([(x, 32), (x + 8, 44)], 16, 44, open_a), w=3, color="white")
        P.stroke([(x, 44), (x + 8, 58)], w=3, color="ink")


@prop("tv", "tv, television, show, screen, broadcast, news channel, series, episode, watch tv, streaming, netflix", "tech")
def _(P):
    P.line(42, 22, 30, 8, w=2.6)
    P.line(58, 22, 70, 8, w=2.6)
    P.rrect(12, 22, 88, 76, r=7, w=3.4, fill="gray")
    P.rrect(18, 28, 72, 70, r=4, w=2.4, fill="lightblue")
    for i in range(5):
        y = 33 + i * 8
        off = (P.t * 30 + i * 13) % 20
        P.line(22 + off * 0.3, y, 60 + off * 0.5, y, w=1.6, color="white")
    P.circle(80, 36, 3, w=2)
    P.circle(80, 48, 3, w=2)
    P.line(30, 76, 26, 86, w=3)
    P.line(70, 76, 74, 86, w=3)


@prop("headphones", "headphones, music, listening, podcast, audio, song, songs, earphones, listen, beats, playlist", "tech")
def _(P):
    P.arc(50, 54, 33, 36, 180, 360, w=5)
    P.rrect(12, 48, 28, 76, r=6, w=3.2, fill="red")
    P.rrect(72, 48, 88, 76, r=6, w=3.2, fill="red")
    for i in range(2):
        y = 30 - ((P.t * 12 + i * 10) % 20)
        x = 50 + (i * 2 - 1) * 10 + wave(P.t, 3, 3, i)
        P.ellipse(x, y + 8, 3.2, 2.4, w=2, fill="ink")
        P.line(x + 3, y + 8, x + 3, y - 2, w=2)


@prop("microphone", "microphone, mic, podcast, speak, speech, voice, sing, singer, interview, talk show, karaoke", "tech")
def _(P):
    P.arc(50, 40, 19, 22, 0, 180, w=3)
    P.line(50, 62, 50, 82, w=3.4)
    P.line(36, 84, 64, 84, w=3.4)
    P.rrect(38, 10, 62, 52, r=12, w=3.4, fill="silver")
    for y in (20, 28, 36):
        P.line(41, y, 59, y, w=1.6)
    k = abs(math.sin(P.t * 4))
    for a0 in (-40, 140):
        P.arc(50, 30, 20 + 6 * k, 22 + 6 * k, a0, a0 + 80, w=2, color="teal")


@prop("gamepad", "game, games, gaming, video game, video games, controller, gamer, play, playstation, xbox, console, nintendo", "tech")
def _(P):
    P.blob([(14, 48), (24, 34), (76, 34), (86, 48), (88, 66), (78, 74), (66, 62), (34, 62), (22, 74), (12, 66)],
           w=3.4, fill="purple")
    P.rect(25, 44, 33, 54, w=2, fill="black")
    P.rect(22, 47, 36, 51, w=2, fill="black")
    press = int(P.t * 3) % 4
    for i, (x, y, c) in enumerate(((68, 42, "red"), (75, 49, "yellow"), (68, 56, "green"), (61, 49, "blue"))):
        P.circle(x, y + (1 if i == press else 0), 3.2, w=1.8, fill=c)


@prop("vr", "vr, virtual reality, vr headset, metaverse, oculus, simulation, virtual world, ar, augmented reality", "tech")
def _(P):
    P.arc(50, 52, 40, 22, 180, 360, w=3)
    P.rrect(14, 38, 86, 68, r=12, w=3.4, fill="gray")
    P.ellipse(34, 53, 12, 9, w=2.6, fill="purple")
    P.ellipse(66, 53, 12, 9, w=2.6, fill="purple")
    P.poly([(45, 68), (50, 60), (55, 68)], w=2.6, fill="gray")
    P.sparkle(34, 53, r=4, w=1.6, color="white")


# ============================================================================================ SCIENCE / SPACE
@prop("dna", "dna, gene, genes, genetic, genetics, biology, evolution, chromosome, heredity, ancestry, mutation", "science")
def _(P):
    ph = P.t * 2
    a, b = [], []
    for i in range(22):
        y = 10 + i * 3.8
        a.append((50 + 18 * math.sin(y * 0.11 + ph), y))
        b.append((50 - 18 * math.sin(y * 0.11 + ph), y))
    for i in range(1, 21, 3):
        P.line(a[i][0], a[i][1], b[i][0], b[i][1], w=2.6, color=("red", "blue", "green", "yellow")[(i // 3) % 4])
    P.curve(a, w=3.6, color="purple")
    P.curve(b, w=3.6, color="teal")


@prop("atom", "atom, atoms, science, physics, nuclear, quantum, energy, particle, electron, proton, molecule, scientific", "science")
def _(P):
    for k in range(3):
        P.ellipse(50, 50, 40, 14, w=2.8, rot=k * 60)
    P.circle(50, 50, 7, w=2.6, fill="red")
    for k in range(3):
        a = math.radians(P.t * 140 + k * 120)
        x, y = 40 * math.cos(a), 14 * math.sin(a)
        r = math.radians(k * 60)
        P.dot(50 + x * math.cos(r) - y * math.sin(r), 50 + x * math.sin(r) + y * math.cos(r), 3, color="blue")


@prop("flask", "chemistry, chemical, experiment, lab, laboratory, potion, test, scientist, formula, reaction, poison", "science")
def _(P):
    P.poly([(30, 70), (70, 70), (78, 84), (22, 84)], w=0.1, fill="green")
    P.poly([(42, 50), (58, 50), (70, 70), (30, 70)], w=0.1, fill="green")
    P.stroke([(42, 12), (42, 38), (20, 84), (80, 84), (58, 38), (58, 12)], w=3.4)
    P.line(37, 12, 63, 12, w=3.4)
    for i in range(4):
        y = 80 - ((P.t * 22 + i * 9) % 50)
        P.circle(50 + wave(P.t, 4, 4, i), y, 2.2 + i * 0.6, w=1.8)


@prop("microscope", "microscope, research, cells, cell, scientist, study, studies, laboratory test, bacteria, germs", "science")
def _(P):
    P.rrect(24, 82, 76, 90, r=3, w=3.2, fill="gray")
    P.curve([(62, 82), (66, 66), (64, 50), (56, 38)], w=4.4)
    P.rect(30, 62, 60, 66, w=2.6, fill="silver")
    tube = rot([(40, 12), (52, 12), (52, 50), (40, 50)], 46, 50, -20)
    P.poly(tube, w=3.2, fill="silver")
    P.circle(53, 47, 4, w=2.4, fill="ink")
    P.dot(45, 66, 2, color="green")


@prop("magnet", "magnet, magnetic, attract, attraction, pull, magnetism", "science")
def _(P):
    P.stroke([(28, 20), (28, 58)], w=1)
    P.poly([(20, 20), (36, 20), (36, 58), (40, 66), (50, 70), (60, 66), (64, 58), (64, 20), (80, 20), (80, 60),
            (72, 76), (50, 84), (28, 76), (20, 60)], w=3.4, fill="red")
    P.rect(20, 14, 36, 24, w=3, fill="silver")
    P.rect(64, 14, 80, 24, w=3, fill="silver")
    k = abs(math.sin(P.t * 4))
    for x in (28, 72):
        P.line(x - 6, 8 - 4 * k, x - 9, 3 - 4 * k, w=2, color="yellow")
        P.line(x + 6, 8 - 4 * k, x + 9, 3 - 4 * k, w=2, color="yellow")


@prop("telescope", "telescope, astronomy, stargazing, observatory, astronomer, observe, look at the stars", "science")
def _(P):
    P.line(50, 56, 34, 88, w=3.2)
    P.line(50, 56, 66, 88, w=3.2)
    P.line(50, 56, 50, 88, w=3.2)
    tube = rot([(20, 40), (80, 40), (80, 52), (20, 52)], 50, 46, -28)
    P.poly(tube, w=3.4, fill="blue")
    P.poly(rot([(76, 37), (86, 37), (86, 55), (76, 55)], 50, 46, -28), w=3, fill="silver")
    P.sparkle(88, 12, r=6, color="yellow", phase=1)


@prop("rocket", "rocket, launch, spacex, space travel, startup, growth, blast off, takeoff, nasa, missile, to the moon", "science")
def _(P):
    sh = wave(P.t, 30, 0.8)
    f = 1 + 0.25 * math.sin(P.t * 18)
    P.poly([(42 + sh, 72), (58 + sh, 72), (50 + sh, 72 + 18 * f)], w=2.4, fill="orange")
    P.poly([(46 + sh, 72), (54 + sh, 72), (50 + sh, 72 + 10 * f)], w=1.6, fill="yellow")
    P.poly([(36 + sh, 54), (26 + sh, 72), (36 + sh, 70)], w=3, fill="red")
    P.poly([(64 + sh, 54), (74 + sh, 72), (64 + sh, 70)], w=3, fill="red")
    P.poly([(50 + sh, 8), (62 + sh, 26), (64 + sh, 72), (36 + sh, 72), (38 + sh, 26)], w=3.4, fill="lightgray", smooth=False)
    P.circle(50 + sh, 38, 7, w=3, fill="lightblue")


@prop("planet", "planet, planets, saturn, jupiter, mars, space, universe, solar system, outer space, astronomy, galaxy", "science")
def _(P):
    P.circle(50, 50, 22, w=3.4, fill="orange")
    P.arc(50, 50, 20, 20, 200, 250, w=2.2)
    P.arc(50, 56, 18, 8, 10, 170, w=2.2)
    ring = [(50 + 40 * math.cos(math.radians(a)), 50 + 10 * math.sin(math.radians(a))) for a in range(-10, 191, 10)]
    P.stroke(rot(ring, 50, 50, -16), w=3.2, color="yellow")
    P.sparkle(16, 18, r=5, phase=0.3)
    P.sparkle(84, 82, r=4, phase=2.1)
    P.sparkle(82, 20, r=3, phase=4.0)


@prop("ufo", "ufo, ufos, flying saucer, alien sighting, area 51, abduction, uap, unidentified, extraterrestrial craft", "science")
def _(P):
    by = wave(P.t, 2, 3)
    if int(P.t * 6) % 2 == 0:
        for x0, x1 in ((40, 26), (60, 74), (50, 50)):
            P.line(x0, 56 + by, x1, 92, w=1.8, color="yellow")
    P.arc(50, 44 + by, 15, 16, 180, 360, w=3, color="ink")
    P.ellipse(50, 50 + by, 36, 10, w=3.4, fill="gray")
    P.ellipse(50, 41 + by, 14, 7, w=2, fill="lightblue")
    for i, x in enumerate((26, 38, 50, 62, 74)):
        on = (i + int(P.t * 6)) % 2 == 0
        P.dot(x, 51 + by, 2.4, color="yellow" if on else "red")


@prop("alien", "alien, aliens, extraterrestrial, et, martian, outer space being, visitor from space, little green men", "science")
def _(P):
    P.line(40, 22, 32, 8, w=2.4)
    P.line(60, 22, 68, 8, w=2.4)
    P.circle(32, 7, 3, w=2, fill="green")
    P.circle(68, 7, 3, w=2, fill="green")
    P.blob([(50, 16), (72, 24), (80, 44), (70, 70), (56, 86), (44, 86), (30, 70), (20, 44), (28, 24)], w=3.4, fill="green")
    look = wave(P.t, 1.5, 2)
    blink = (int(P.t * 12) % 36) < 2
    for s in (-1, 1):
        if blink:
            P.line(50 + s * 16 - 8, 48, 50 + s * 16 + 6, 48, w=3)
        else:
            P.ellipse(50 + s * 15, 47, 10, 6, w=2.6, fill="black", rot=s * 25)
            P.dot(50 + s * 15 + look, 45, 1.8, color="white")
    P.arc(50, 66, 6, 3, 20, 160, w=2.4)


# ============================================================================================ MONEY / BUSINESS
@prop("money", "money, cash, dollar, dollars, bill, bills, paid, pay, payment, salary, income, earn, earning, cost, costs, price, "
      "profit, rich, wealth, wealthy, million, millions, billion, billions, fortune, payday, bucks", "money")
def _(P):
    for i, dy in enumerate((14, 7, 0)):
        x0, y0 = 12 + i * 3, 30 - dy + wave(P.t, 3, 1.2, i)
        P.rrect(x0, y0, x0 + 72, y0 + 40, r=3, w=3.2, fill="green")
        P.rrect(x0 + 4, y0 + 4, x0 + 68, y0 + 36, r=2, w=1.6)
    cx, cy = 12 + 6 + 36, 30 + 20
    P.circle(cx, cy, 12, w=2.6, fill="lightgray")
    P.text(cx, cy + 1, "$", size=17)


@prop("coins", "coins, coin, savings, change, pennies, gold coins, treasure coins, loose change", "money")
def _(P):
    for i in range(4):
        y = 76 - i * 9
        P.ellipse(40, y, 20, 6, w=2.8, fill="gold")
        P.line(20, y, 20, y + 5, w=2.6)
        P.line(60, y, 60, y + 5, w=2.6)
    hop = abs(math.sin(P.t * 3)) * 10
    P.circle(72, 42 - hop, 14, w=3.2, fill="gold")
    P.text(72, 43 - hop, "$", size=14)


@prop("crypto", "crypto, cryptocurrency, bitcoin, ethereum, blockchain, nft, nfts, token, tokens, web3, mining, dogecoin, altcoin", "money")
def _(P):
    P.circle(50, 50, 34, w=3.6, fill="gold")
    P.circle(50, 50, 26, w=2.2)
    a = P.t * 30
    hexa = [(50 + 13 * math.cos(math.radians(a + k * 60)), 50 + 13 * math.sin(math.radians(a + k * 60))) for k in range(6)]
    P.poly(hexa, w=3, fill="orange")
    for x, y in hexa[::2]:
        P.line(50, 50, x, y, w=2)


@prop("chart_up", "growth, grow, growing, profit, increase, increased, stocks went up, stocks, rise, rising, up, success, gains, "
      "boom, skyrocket, went up, record high, booming", "money")
def _(P):
    P.stroke([(14, 10), (14, 86), (90, 86)], w=3.4)
    P.stroke([(20, 76), (36, 62), (48, 68), (64, 44), (74, 50), (88, 20)], w=4, color="green")
    P.arrow(80, 30, 89, 18, w=4, head=9, color="green")


@prop("chart_down", "crash, crashed, loss, losses, decline, drop, dropped, recession, fall, falling, down, plummet, bankrupt, "
      "collapse, market crash, losing money, debt", "money")
def _(P):
    P.stroke([(14, 10), (14, 86), (90, 86)], w=3.4)
    P.stroke([(20, 20), (34, 34), (46, 28), (60, 52), (72, 46), (86, 76)], w=4, color="red")
    P.arrow(78, 64, 87, 78, w=4, head=9, color="red")


@prop("bar_chart", "statistics, stats, data, chart, graph, compare, comparison, survey, results, numbers, analytics, study shows", "money")
def _(P):
    P.stroke([(12, 10), (12, 86), (90, 86)], w=3.4)
    g = min(1.0, P.t / 1.0)
    for i, (h, c) in enumerate(((28, "blue"), (44, "teal"), (36, "purple"), (64, "orange"))):
        x = 22 + i * 17
        hh = h * g
        P.rect(x, 86 - hh, x + 11, 86, w=2.8, fill=c)


@prop("pie_chart", "percent, percentage, share, split, portion, market share, majority, minority, half, fraction, ratio", "money")
def _(P):
    P.circle(46, 52, 32, w=3.4, fill="blue")
    P.poly([(46, 52)] + [(46 + 32 * math.cos(math.radians(a)), 52 + 32 * math.sin(math.radians(a))) for a in range(-90, 31, 10)],
           w=3, fill="yellow")
    off = 4 + 2 * math.sin(P.t * 3)
    ox, oy = off * math.cos(math.radians(70)), off * math.sin(math.radians(70))
    P.poly([(46 + ox, 52 + oy)] + [(46 + ox + 32 * math.cos(math.radians(a)), 52 + oy + 32 * math.sin(math.radians(a)))
                                   for a in range(30, 111, 10)], w=3, fill="red")


@prop("bank", "bank, banks, finance, financial, loan, loans, federal reserve, wall street, government, court house, institution, mortgage", "money")
def _(P):
    P.poly([(10, 34), (50, 10), (90, 34)], w=3.4, fill="lightgray")
    P.rect(14, 34, 86, 40, w=3, fill="lightgray")
    for x in (22, 38, 54, 70):
        P.rect(x, 42, x + 8, 76, w=2.6, fill="paper")
    P.rect(10, 78, 90, 84, w=3, fill="lightgray")
    P.rect(6, 86, 94, 92, w=3, fill="lightgray")
    P.circle(50, 25, 6, w=2.2, fill="gold")
    P.text(50, 25.5, "$", size=8)


@prop("wallet", "wallet, spend, spending, budget, broke, purse, pocket money, saving money, expenses", "money")
def _(P):
    P.rrect(20, 22 + wave(P.t, 3, 2), 70, 46, r=2, w=2.6, fill="green")
    P.rrect(12, 34, 88, 82, r=8, w=3.4, fill="brown")
    P.rrect(56, 48, 92, 66, r=6, w=3, fill="brown")
    P.circle(66, 57, 3.2, w=2.2, fill="gold")


@prop("credit_card", "credit card, credit, card, debit card, payment card, debt, swipe, online payment, card payment, visa", "money")
def _(P):
    a = wave(P.t, 1.5, 4)
    P.poly(rot([(12, 26), (88, 26), (88, 76), (12, 76)], 50, 51, a), w=3.4, fill="blue")
    P.poly(rot([(20, 38), (34, 38), (34, 50), (20, 50)], 50, 51, a), w=2.2, fill="gold")
    for i in range(4):
        P.stroke(rot([(20 + i * 16, 61), (31 + i * 16, 61)], 50, 51, a), w=2.6, color="white")
    P.stroke(rot([(20, 69), (50, 69)], 50, 51, a), w=2, color="white")


@prop("shopping_cart", "shopping, shop, buy, buying, store, cart, ecommerce, online shopping, purchase, groceries, consumer, amazon", "money")
def _(P):
    roll = P.t * 120
    P.rect(36, 30, 50, 44, w=2.4, fill="orange")
    P.rect(52, 26, 66, 44, w=2.4, fill="teal")
    P.stroke([(8, 18), (20, 18), (30, 66), (78, 66)], w=3.4)
    P.poly([(22, 28), (88, 28), (80, 56), (28, 56)], w=3.2)
    for x in (34, 72):
        P.circle(x, 76, 6, w=3)
        a = math.radians(roll)
        P.line(x, 76, x + 5 * math.cos(a), 76 + 5 * math.sin(a), w=1.8)


@prop("briefcase", "business, job, jobs, work, working, career, office, company, companies, ceo, employee, corporate, boss, hired", "money")
def _(P):
    P.rrect(36, 18, 64, 34, r=4, w=3.2)
    P.rrect(10, 30, 90, 84, r=7, w=3.4, fill="brown")
    P.line(10, 52, 90, 52, w=2.6)
    P.rect(44, 46, 56, 58, w=2.6, fill="gold")


@prop("handshake", "deal, agreement, partnership, partners, trust, contract, hire, agree, cooperation, teamwork, alliance, negotiation", "money")
def _(P):
    sh = wave(P.t, 5, 2)
    P.poly([(4, 70), (26, 48 + sh), (36, 58 + sh), (14, 82)], w=3.2, fill="blue")
    P.poly([(96, 70), (74, 48 + sh), (64, 58 + sh), (86, 82)], w=3.2, fill="red")
    P.blob([(26, 48 + sh), (42, 38 + sh), (60, 40 + sh), (74, 48 + sh), (66, 62 + sh), (48, 66 + sh), (34, 60 + sh)],
           w=3.2, fill="skin")
    for i in range(3):
        P.curve([(44 + i * 7, 44 + sh), (48 + i * 7, 52 + sh), (46 + i * 7, 60 + sh)], w=2)


@prop("piggy_bank", "save, saving, savings, piggy bank, invest, investing, investment, retirement, nest egg, frugal", "money")
def _(P):
    cy = 80 - ((P.t * 30) % 46) if P.t > 0.8 else 34
    if cy < 46:
        P.circle(52, cy, 7, w=2.4, fill="gold")
    P.ellipse(50, 58, 32, 22, w=3.4, fill="pink")
    P.ellipse(82, 58, 7, 9, w=3, fill="pink")
    P.dot(80, 56, 1.4)
    P.dot(84, 60, 1.4)
    P.poly([(30, 40), (34, 26), (42, 38)], w=2.8, fill="pink")
    P.dot(66, 50, 2.2)
    P.line(44, 37, 60, 37, w=3)
    for x in (30, 44, 58, 70):
        P.line(x, 76, x, 88, w=3.4)
    P.curve([(18, 54), (12, 50), (14, 44), (10, 40)], w=2.4)


@prop("diamond", "diamond, diamonds, rich, luxury, valuable, jewel, jewelry, gem, gems, precious, expensive, crystal", "money")
def _(P):
    P.poly([(28, 34), (72, 34), (90, 46), (50, 90), (10, 46)], w=3.4, fill="lightblue")
    P.stroke([(10, 46), (90, 46)], w=2.4)
    P.stroke([(28, 34), (38, 46), (50, 34), (62, 46), (72, 34)], w=2.2)
    P.stroke([(38, 46), (50, 90), (62, 46)], w=2.2)
    P.sparkle(78, 26, r=7, phase=0)
    P.sparkle(22, 76, r=5, phase=2)


@prop("crown", "king, queen, royal, royalty, crown, winner, ruler, empire, kingdom, monarch, prince, princess, emperor", "money")
def _(P):
    P.poly([(14, 74), (12, 30), (32, 50), (50, 22), (68, 50), (88, 30), (86, 74)], w=3.6, fill="gold")
    P.rect(14, 74, 86, 84, w=3.2, fill="gold")
    for x, c in ((32, "red"), (50, "blue"), (68, "green")):
        P.circle(x, 63, 4.2, w=2.2, fill=c)
    for x, y in ((12, 30), (50, 22), (88, 30)):
        P.circle(x, y - 4, 3.6, w=2.2, fill="gold")
    P.sparkle(80, 16, r=6, phase=1)


@prop("trophy", "trophy, win, won, winning, champion, championship, award, prize, first place, victory, cup, best", "money")
def _(P):
    P.arc(26, 34, 12, 14, 90, 270, w=3.4)
    P.arc(74, 34, 12, 14, -90, 90, w=3.4)
    P.poly([(26, 16), (74, 16), (70, 44), (58, 56), (42, 56), (30, 44)], w=3.6, fill="gold")
    P.rect(45, 56, 55, 70, w=3, fill="gold")
    P.rrect(30, 70, 70, 84, r=3, w=3.4, fill="brown")
    P.star(50, 34, 8, 3.4, w=2, fill="yellow")
    P.sparkle(84, 14, r=6, phase=0.5)
    P.sparkle(16, 62, r=4, phase=2.5)


@prop("medal", "medal, medals, olympics, olympic, achievement, gold medal, honor, honour, accomplished, first", "money")
def _(P):
    P.poly([(30, 8), (44, 8), (56, 46), (44, 50)], w=3, fill="red")
    P.poly([(70, 8), (56, 8), (44, 46), (56, 50)], w=3, fill="blue")
    sw = wave(P.t, 2.5, 4)
    P.circle(50 + sw * 0.3, 64, 21, w=3.4, fill="gold")
    P.star(50 + sw * 0.3, 64, 11, 4.6, w=2.2, fill="yellow")


@prop("target", "goal, goals, target, aim, focus, bullseye, strategy, objective, mission, plan, accuracy, hit the target", "money")
def _(P):
    P.circle(46, 54, 34, w=3.4, fill="red")
    P.circle(46, 54, 24, w=2.8, fill="paper")
    P.circle(46, 54, 14, w=2.8, fill="red")
    P.circle(46, 54, 5, w=2.4, fill="paper")
    hit = min(1, P.t / 0.5)
    sx, sy = 46 + 40 * (1 - hit), 54 - 40 * (1 - hit)
    wob = wave(P.t, 25, 2) * (1 if 0.5 < P.t < 1.0 else 0)
    P.stroke([(sx, sy), (sx + 32, sy - 32 + wob)], w=3.2)
    P.stroke([(sx + 26, sy - 34 + wob), (sx + 36, sy - 36 + wob), (sx + 34, sy - 26 + wob)], w=2.6, color="yellow")


@prop("megaphone", "announce, announcement, marketing, advertising, ads, shout, attention, broadcast, loud, promote, campaign, protest", "money")
def _(P):
    P.poly([(20, 42), (66, 18), (66, 82), (20, 58)], w=3.4, fill="red")
    P.rect(10, 40, 22, 60, w=3, fill="gray")
    P.line(32, 58, 36, 76, w=3.4)
    k = (P.t * 2) % 1
    for i in range(3):
        r = 10 + i * 9 + k * 6
        P.arc(66, 50, r, r * 1.2, -45, 45, w=2.4, color="orange")


@prop("gift", "gift, gifts, present, presents, free, bonus, giveaway, birthday present, surprise, reward, christmas", "money")
def _(P):
    hop = max(0, math.sin(P.t * 4)) * 8 if P.t > 0.8 else 0
    P.rect(18, 46, 82, 88, w=3.4, fill="red")
    P.rect(46, 46, 54, 88, w=2.2, fill="yellow")
    P.rect(14, 34 - hop, 86, 46 - hop, w=3.2, fill="red")
    P.rect(46, 34 - hop, 54, 46 - hop, w=2, fill="yellow")
    P.blob([(50, 34 - hop), (36, 20 - hop), (30, 28 - hop), (38, 34 - hop)], w=2.6, fill="yellow")
    P.blob([(50, 34 - hop), (64, 20 - hop), (70, 28 - hop), (62, 34 - hop)], w=2.6, fill="yellow")


@prop("price_tag", "sale, discount, deal, deals, cheap, price tag, offer, bargain, black friday, coupon, promo, percent off", "money")
def _(P):
    a = wave(P.t, 2.5, 8)
    tag = rot([(30, 22), (84, 22), (84, 70), (30, 70), (14, 46)], 14, 46, a)
    P.poly(tag, w=3.4, fill="yellow")
    hx, hy = rot([(26, 46)], 14, 46, a)[0]
    P.circle(hx, hy, 3.4, w=2.2, fill="paper")
    P.curve([(hx, hy), (8, 30), (6, 14)], w=2)
    cx, cy = rot([(57, 46)], 14, 46, a)[0]
    P.text(cx, cy, "%", size=24, color="red")


# =================================================================================================== TIME
@prop("hourglass", "time running out, deadline, waiting, wait, hourglass, patience, countdown, running out of time, time is ticking", "time")
def _(P):
    k = (P.t * 0.25) % 1
    P.rect(22, 8, 78, 14, w=3.2, fill="brown")
    P.rect(22, 86, 78, 92, w=3.2, fill="brown")
    top = 34 * (1 - k)
    if top > 2:
        P.poly([(50 - top * 0.7, 48 - top), (50 + top * 0.7, 48 - top), (50, 48)], w=0.1, fill="gold")
    bot = 30 * k + 4
    P.poly([(50 - bot * 0.8, 84), (50 + bot * 0.8, 84), (50, 84 - bot * 0.7)], w=0.1, fill="gold")
    P.line(50, 50, 50, 84 - bot * 0.7, w=1.6, color="gold")
    P.stroke([(28, 14), (28, 24), (48, 48), (28, 74), (28, 86)], w=3.2)
    P.stroke([(72, 14), (72, 24), (52, 48), (72, 74), (72, 86)], w=3.2)


@prop("clock", "time, clock, hour, hours, late, schedule, minute, minutes, o'clock, timing, on time, punctual, years later", "time")
def _(P):
    P.circle(50, 50, 38, w=3.6, fill="cream")
    for i in range(12):
        a = math.radians(i * 30)
        r1 = 31 if i % 3 else 27
        P.line(50 + r1 * math.cos(a), 50 + r1 * math.sin(a), 50 + 35 * math.cos(a), 50 + 35 * math.sin(a), w=2.4)
    am = math.radians(-90 + P.t * 120)
    ah = math.radians(-90 + 60 + P.t * 10)
    P.line(50, 50, 50 + 28 * math.cos(am), 50 + 28 * math.sin(am), w=2.8, color="red")
    P.line(50, 50, 50 + 18 * math.cos(ah), 50 + 18 * math.sin(ah), w=3.6)
    P.dot(50, 50, 3)


@prop("calendar", "date, calendar, day, days, year, years, month, months, event, schedule, appointment, anniversary, weekend, weekday", "time")
def _(P):
    P.rrect(14, 18, 86, 88, r=6, w=3.4, fill="paper")
    P.rect(14, 18, 86, 36, w=3, fill="red")
    for x in (30, 50, 70):
        P.line(x, 10, x, 24, w=3.4)
    for r in range(3):
        for c in range(5):
            P.dot(24 + c * 13, 48 + r * 13, 2.2)
    if P.t > 0.5:
        P.ellipse(50, 61, 9, 7, w=2.8, color="red")


@prop("alarm_clock", "alarm, wake up, waking up, morning, early, alarm clock, deadline alert, too late, overslept", "time")
def _(P):
    sh = wave(P.t, 30, 3) if int(P.t * 2) % 2 == 0 and P.t > 0.8 else 0
    cx = 50 + sh
    P.circle(cx - 22, 22, 9, w=3, fill="red")
    P.circle(cx + 22, 22, 9, w=3, fill="red")
    P.line(cx - 22, 84, cx - 28, 92, w=3.4)
    P.line(cx + 22, 84, cx + 28, 92, w=3.4)
    P.circle(cx, 54, 32, w=3.6, fill="cream")
    P.line(cx, 54, cx, 34, w=3.4)
    P.line(cx, 54, cx + 14, 60, w=3)
    if sh:
        for s in (-1, 1):
            P.line(50 + s * 38, 30, 50 + s * 46, 24, w=2.4, color="orange")
            P.line(50 + s * 40, 40, 50 + s * 48, 40, w=2.4, color="orange")
