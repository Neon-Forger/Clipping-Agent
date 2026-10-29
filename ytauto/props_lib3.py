"""Prop library part 3: nature & weather, animals, food & health, transport, places & buildings."""
import math

from .props import prop, rot, scale, wave


# ============================================================================================ NATURE / WEATHER
@prop("sun", "sun, sunny, summer, hot, heat, heatwave, day, daytime, sunshine, sunrise, sunset, solar, warm", "nature")
def _(P):
    a0 = P.t * 25
    for i in range(10):
        a = math.radians(a0 + i * 36)
        r2 = 44 + (3 if i % 2 else 0) * math.sin(P.t * 4)
        P.line(50 + 30 * math.cos(a), 50 + 30 * math.sin(a), 50 + r2 * math.cos(a), 50 + r2 * math.sin(a), w=3.4, color="orange")
    P.circle(50, 50, 24, w=3.6, fill="yellow")
    for x in (42, 58):
        P.arc(x, 46, 4, 3, 200, 340, w=2.4)
    P.arc(50, 54, 9, 7, 20, 160, w=2.6)


@prop("moon", "moon, night, nighttime, lunar, midnight, dark night, full moon, sleep time, crescent, moonlight", "nature")
def _(P):
    pts = [(50 + 34 * math.cos(math.radians(a)), 50 + 34 * math.sin(math.radians(a))) for a in range(60, 301, 10)]
    pts += [(62 + 26 * math.cos(math.radians(a)), 46 + 26 * math.sin(math.radians(a))) for a in range(250, 109, -10)]
    P.poly(pts, w=3.4, fill="yellow")
    P.sparkle(78, 22, r=6, phase=0)
    P.sparkle(84, 70, r=4, phase=2)
    P.sparkle(66, 86, r=3, phase=4)


@prop("star", "star, stars, famous, fame, celebrity, celebrities, rating, rated, favorite, shine, five stars, superstar, iconic", "nature")
def _(P):
    s = 1 + 0.08 * math.sin(P.t * 4)
    P.star(50, 52, 38 * s, 16 * s, w=3.8, fill="yellow", rot=-90 + wave(P.t, 2, 6))
    P.arc(42, 44, 6, 4, 200, 340, w=2)
    P.arc(58, 44, 6, 4, 200, 340, w=2)
    P.sparkle(86, 16, r=7, phase=1)
    P.sparkle(14, 80, r=5, phase=3)


@prop("fire", "fire, fires, burn, burned, burning, hot, flame, flames, wildfire, destroyed, lit, trending, on fire, blaze, arson", "nature")
def _(P):
    f1 = wave(P.t, 9, 5)
    f2 = wave(P.t, 13, 4, 1)
    P.poly([(50, 8 + f1), (66, 30), (76, 52), (72, 74), (58, 88), (42, 88), (28, 74), (24, 52), (36, 36), (40, 48), (46, 26)],
           w=3.6, fill="orange", smooth=True)
    P.poly([(50, 40 + f2), (60, 56), (62, 72), (54, 84), (46, 84), (38, 72), (42, 56), (48, 62)], w=2.8, fill="yellow", smooth=True)


@prop("water_drop", "water, drop, drops, rain drop, liquid, drink, drinking water, hydrate, hydration, thirsty, fluid, wet", "nature")
def _(P):
    y = (P.t * 1.3) % 1
    sq = 1 - 0.15 * max(0, math.sin(y * math.pi * 2)) if y > 0.75 else 1
    P.poly(scale([(50, 10), (66, 40), (72, 58), (64, 76), (50, 82), (36, 76), (28, 58), (34, 40)], 50, 82, sq), w=3.6,
           fill="lightblue", smooth=True)
    P.arc(42, 58, 8, 10, 120, 200, w=2.6, color="white")
    if y > 0.75:
        r = (y - 0.75) * 120
        P.ellipse(50, 88, 10 + r, 3 + r * 0.2, w=2, color="blue")


@prop("lightning", "lightning, electricity, electric, power, energy, fast, speed, quick, storm, shock, shocking, thunder, zap, voltage", "nature")
def _(P):
    on = int(P.t * 5) % 3 != 0 or P.t < 0.9
    P.poly([(58, 8), (24, 54), (46, 54), (36, 92), (76, 40), (52, 40), (66, 8)], w=3.6, fill="yellow" if on else "orange")
    if on and P.t > 0.9:
        P.line(16, 30, 8, 26, w=2.4, color="yellow")
        P.line(84, 62, 92, 66, w=2.4, color="yellow")


@prop("snowflake", "snow, snowing, cold, winter, freeze, freezing, frozen, ice, icy, chill, frost, blizzard, arctic", "nature")
def _(P):
    a0 = P.t * 20
    for k in range(6):
        a = math.radians(a0 + k * 60)
        ex, ey = 50 + 38 * math.cos(a), 50 + 38 * math.sin(a)
        P.line(50, 50, ex, ey, w=3.6, color="blue")
        for d in (0.55, 0.8):
            mx, my = 50 + 38 * d * math.cos(a), 50 + 38 * d * math.sin(a)
            for s in (-1, 1):
                b = a + s * math.radians(45)
                P.line(mx, my, mx + 10 * math.cos(b), my + 10 * math.sin(b), w=2.6, color="blue")
    P.circle(50, 50, 5, w=2, fill="lightblue")


@prop("tree", "tree, trees, nature, forest, environment, plant, plants, climate, climate change, oak, woods, deforestation, eco", "nature")
def _(P):
    sw = wave(P.t, 1.6, 2)
    P.poly([(44, 92), (46, 54), (54, 54), (56, 92)], w=3.2, fill="brown")
    P.blob([(50 + sw, 10), (70 + sw, 16), (82 + sw, 32), (80 + sw, 50), (66 + sw, 62), (50 + sw, 60), (34 + sw, 62), (20 + sw, 50),
            (18 + sw, 32), (30 + sw, 16)], w=3.6, fill="green")
    for x, y in ((38, 30), (60, 26), (64, 46), (40, 48)):
        P.circle(x + sw, y, 3, w=1.6, fill="red")


@prop("flower", "flower, flowers, spring, garden, gardening, bloom, blooming, beauty, beautiful, rose, roses, petals, gift flowers", "nature")
def _(P):
    sw = wave(P.t, 2, 3)
    P.curve([(50, 92), (48, 74), (52 + sw * 0.5, 56)], w=3.4, color="green")
    P.blob([(48, 76), (32, 66), (28, 74), (40, 80)], w=2.4, fill="green")
    cx, cy = 52 + sw, 38
    for k in range(6):
        a = math.radians(k * 60 + P.t * 15)
        P.ellipse(cx + 16 * math.cos(a), cy + 16 * math.sin(a), 11, 8, w=2.6, fill="pink", rot=math.degrees(a))
    P.circle(cx, cy, 9, w=2.6, fill="yellow")


@prop("leaf", "leaf, leaves, eco, green, organic, sustainable, vegan, natural, plant based, autumn, fall season", "nature")
def _(P):
    a = wave(P.t, 2, 10)
    pts = rot([(16, 84), (20, 50), (40, 24), (70, 12), (88, 14), (86, 36), (72, 62), (46, 80)], 50, 50, a)
    P.poly(pts, w=3.6, fill="green", smooth=True)
    P.stroke(rot([(16, 84), (50, 50), (82, 18)], 50, 50, a), w=2.6)
    for (x1, y1), (x2, y2) in (((40, 60), (34, 42)), ((52, 48), (48, 30)), ((40, 60), (60, 64)), ((52, 48), (70, 50))):
        P.stroke(rot([(x1, y1), (x2, y2)], 50, 50, a), w=1.8)


@prop("mountain", "mountain, mountains, climb, everest, peak, summit, hike, challenge, alps, expedition, altitude, cliff, climbers", "nature")
def _(P):
    P.poly([(6, 88), (40, 24), (56, 50), (66, 36), (94, 88)], w=3.6, fill="gray")
    P.poly([(40, 24), (30, 42), (36, 40), (42, 46), (48, 38)], w=2.4, fill="white")
    P.poly([(66, 36), (60, 46), (66, 44), (72, 48)], w=2, fill="white")
    k = (P.t * 0.3) % 1
    P.line(40, 24, 40, 10, w=2.2)
    P.poly([(40, 10), (52 + wave(P.t, 6, 2), 13), (40, 17)], w=1.8, fill="red")
    P.dot(20 + k * 18, 82 - k * 50, 2.2, color="red")


@prop("wave", "wave, waves, sea, ocean, tsunami, surf, surfing, tide, flood, flooding, storm surge, beach", "nature")
def _(P):
    ph = P.t * 3
    P.poly([(8, 86), (8, 60), (20, 40), (36, 24), (54, 18), (70, 22), (80, 34), (74, 44), (64, 40), (56, 46), (52, 60),
            (62, 70), (92, 70), (92, 86)], w=3.6, fill="blue", smooth=True)
    for i in range(2):
        y = 78 + i * 6
        P.stroke([(8 + x * 4, y + math.sin(x * 0.8 + ph) * 2) for x in range(22)], w=2, color="white")
    P.circle(76, 30 + wave(P.t, 6, 2), 3, w=1.6, fill="white")
    P.circle(84, 38 + wave(P.t, 5, 2, 1), 2, w=1.4, fill="white")


@prop("volcano", "volcano, volcanoes, eruption, erupt, erupted, lava, magma, explosion, natural disaster, pompeii, ash", "nature")
def _(P):
    P.poly([(6, 90), (36, 30), (64, 30), (94, 90)], w=3.6, fill="brown")
    P.poly([(36, 30), (44, 46), (50, 38), (56, 50), (64, 30)], w=2.6, fill="orange")
    for i in range(5):
        k = (P.t * 1.2 + i * 0.2) % 1
        x = 50 + (i - 2) * 9 * k
        y = 28 - 30 * math.sin(k * math.pi) + 10 * k
        P.circle(x, y, 3.4 * (1 - k * 0.5), w=1.6, fill=("orange", "red", "yellow")[i % 3])
    P.blob([(36, 12), (44, 4), (58, 6), (66, 14), (52, 18)], w=2.2, fill="gray")


@prop("tornado", "tornado, tornadoes, hurricane, storm, twister, chaos, cyclone, typhoon, natural disaster, wind, windy, whirlwind", "nature")
def _(P):
    for i in range(7):
        y = 14 + i * 11
        w = 40 - i * 5
        x = 50 + math.sin(P.t * 3 + i * 0.6) * (i * 1.6)
        P.arc(x, y, w, 5, 0, 330 - i * 10, w=3.2, color="gray")
    for i in range(3):
        a = P.t * 4 + i * 2
        P.rect(50 + 40 * math.cos(a) - 2, 40 + 10 * math.sin(a) - 2, 50 + 40 * math.cos(a) + 2, 40 + 10 * math.sin(a) + 2, w=1.6,
               fill="brown")


@prop("globe", "world, earth, global, globally, planet earth, international, countries, worldwide, around the world, humanity, geography", "nature")
def _(P):
    P.circle(50, 50, 38, w=3.6, fill="lightblue")
    sh = (P.t * 8) % 40
    for x0, pts in ((20, [(0, 0), (12, -10), (22, -4), (18, 10), (6, 14)]), (52, [(0, -6), (14, -12), (22, 0), (12, 16), (2, 8)])):
        xx = ((x0 + sh - 12) % 80) + 10
        land = [(xx + dx, 46 + dy) for dx, dy in pts]
        if all(math.hypot(px - 50, py - 50) < 36 for px, py in land):
            P.poly(land, w=2.4, fill="green", smooth=True)
    P.arc(50, 50, 38, 12, 0, 360, w=1.6)
    P.arc(50, 50, 14, 38, -90, 90, w=1.6)


@prop("rainbow", "rainbow, hope, pride, colorful, colourful, after the storm, happy ending, optimism, magic sky", "nature")
def _(P):
    for i, c in enumerate(("red", "orange", "yellow", "green", "blue", "purple")):
        r = 40 - i * 4.6
        P.arc(50, 74, r, r, 180, 360, w=4.4, color=c)
    for x in (12, 88):
        P.blob([(x - 12, 76), (x - 8, 66), (x, 64), (x + 8, 66), (x + 12, 76)], w=2.6, fill="white")


@prop("rain_cloud", "rain, raining, rainy, weather, cloudy, gloomy, storm cloud, bad weather, downpour, wet weather", "nature")
def _(P):
    for i in range(6):
        x = 24 + i * 10
        y = 58 + ((P.t * 50 + i * 13) % 30)
        P.line(x, y, x - 3, y + 8, w=2.4, color="blue")
    P.blob([(14, 50), (12, 38), (22, 28), (34, 28), (40, 16), (56, 12), (68, 20), (72, 30), (84, 32), (90, 44), (84, 54)],
           w=3.6, fill="gray")


# ================================================================================================ ANIMALS
@prop("cat", "cat, cats, kitten, kitty, pet cat, feline, meow", "animals")
def _(P):
    tail = wave(P.t, 3, 10)
    P.curve([(70, 80), (84, 70), (88 + tail * 0.3, 50), (80 + tail, 36)], w=4.4)
    P.ellipse(52, 70, 22, 18, w=3.4, fill="orange")
    P.poly([(30, 30), (34, 12), (44, 24)], w=3, fill="orange")
    P.poly([(70, 30), (66, 12), (56, 24)], w=3, fill="orange")
    P.circle(50, 38, 20, w=3.4, fill="orange")
    blink = (int(P.t * 12) % 30) < 2
    for x in (42, 58):
        if blink:
            P.line(x - 4, 36, x + 4, 36, w=2.4)
        else:
            P.ellipse(x, 36, 3, 4.4, w=2, fill="ink")
    P.poly([(48, 44), (52, 44), (50, 47)], w=1.6, fill="pink")
    for s in (-1, 1):
        P.line(50 + s * 6, 47, 50 + s * 22, 44, w=1.6)
        P.line(50 + s * 6, 49, 50 + s * 22, 51, w=1.6)


@prop("dog", "dog, dogs, puppy, puppies, pet dog, pets, canine, woof, loyal, best friend", "animals")
def _(P):
    wag = wave(P.t, 12, 12)
    P.stroke([(76, 60), (88, 48 + wag * 0.3), (90 + wag * 0.4, 38)], w=4)
    P.ellipse(56, 66, 24, 16, w=3.4, fill="brown")
    for x in (40, 52, 64, 74):
        P.line(x, 78, x, 90, w=3.4)
    P.circle(34, 44, 18, w=3.4, fill="brown")
    P.blob([(18, 36), (14, 52), (22, 58), (24, 42)], w=2.6, fill="black")
    P.ellipse(24, 52, 8, 6, w=2.4, fill="cream")
    P.dot(18, 50, 2.6)
    P.dot(36, 40, 2.4)
    if int(P.t * 3) % 2 == 0:
        P.poly([(24, 58), (28, 58), (26, 66)], w=1.6, fill="pink")


@prop("fish", "fish, fishes, fishing, sea creature, marine life, aquarium, goldfish, salmon, seafood", "animals")
def _(P):
    x = wave(P.t, 1.4, 6)
    tail = wave(P.t, 9, 6)
    P.poly([(72 + x, 50), (90 + x, 36 + tail), (88 + x, 64 + tail)], w=3.2, fill="orange")
    P.ellipse(48 + x, 50, 28, 18, w=3.6, fill="orange")
    P.dot(30 + x, 46, 3)
    P.arc(48 + x, 50, 10, 14, -60, 60, w=2)
    P.poly([(46 + x, 33), (58 + x, 22), (62 + x, 35)], w=2.4, fill="orange")
    for i in range(3):
        k = (P.t * 0.8 + i * 0.33) % 1
        P.circle(16 + x - k * 6, 40 - k * 30, 2 + i, w=1.6)


@prop("bird", "bird, birds, fly, flying, freedom, free, tweet, wings, migrate, flock, sparrow, pigeon, eagle", "animals")
def _(P):
    flap = math.sin(P.t * 8)
    by = wave(P.t, 2, 3)
    P.ellipse(50, 56 + by, 24, 15, w=3.4, fill="blue")
    P.circle(72, 44 + by, 11, w=3, fill="blue")
    P.poly([(82, 42 + by), (94, 46 + by), (82, 50 + by)], w=2.4, fill="yellow")
    P.dot(74, 41 + by, 2.2)
    P.poly([(42, 50 + by), (30, 50 + by - 26 * flap), (58, 50 + by)], w=3, fill="lightblue")
    P.poly([(26, 54 + by), (8, 46 + by), (10, 62 + by)], w=2.6, fill="blue")


@prop("shark", "shark, sharks, jaws, predator, danger in the water, attack, shark attack, deep sea predator", "animals")
def _(P):
    x = wave(P.t, 1.2, 10)
    P.poly([(14 + x, 54), (40 + x, 40), (52 + x, 18), (58 + x, 40), (80 + x, 46), (92 + x, 56), (80 + x, 62), (60 + x, 66),
            (40 + x, 64)], w=3.6, fill="gray", smooth=True)
    P.poly([(14 + x, 54), (4 + x, 40), (8 + x, 56), (4 + x, 70)], w=3, fill="gray")
    P.dot(76 + x, 52, 2.4)
    P.stroke([(74 + x, 60), (78 + x, 57), (82 + x, 60), (86 + x, 57), (90 + x, 59)], w=2)
    for i in range(3):
        P.arc(56 + x - i * 4, 52, 2, 6, -60, 60, w=1.6)
    P.stroke([(4 + i * 6, 80 + math.sin(i + P.t * 3) * 2) for i in range(16)], w=2.4, color="blue")


@prop("snake", "snake, snakes, serpent, venom, venomous, python, cobra, viper, slithered, sneaky, betrayal snake", "animals")
def _(P):
    ph = P.t * 3
    body = [(10 + i * 5, 62 + math.sin(i * 0.6 + ph) * 12) for i in range(15)]
    P.stroke(body, w=10, color="green")
    P.stroke(body, w=2, color="darkgreen")
    hx, hy = body[-1]
    P.ellipse(hx + 6, hy - 2, 10, 7, w=3, fill="green")
    P.dot(hx + 8, hy - 5, 2)
    if int(P.t * 4) % 2 == 0:
        P.stroke([(hx + 15, hy), (hx + 22, hy), (hx + 25, hy - 3)], w=1.8, color="red")
        P.stroke([(hx + 22, hy), (hx + 25, hy + 3)], w=1.8, color="red")


@prop("spider", "spider, spiders, web, spider web, scary, creepy, arachnid, tarantula, creepy crawly", "animals")
def _(P):
    y = 48 + wave(P.t, 1.6, 8)
    P.line(50, 0, 50, y - 12, w=1.6)
    for s in (-1, 1):
        for i in range(4):
            a = -40 + i * 26
            k = wave(P.t, 8, 4, i)
            P.stroke([(50 + s * 8, y), (50 + s * 22, y - 10 + i * 8 + k), (50 + s * 32, y + i * 9 - 4 + k)], w=2.6)
    P.ellipse(50, y + 6, 12, 14, w=3.2, fill="black")
    P.circle(50, y - 10, 8, w=2.8, fill="black")
    P.dot(47, y - 12, 1.6, color="white")
    P.dot(53, y - 12, 1.6, color="white")


@prop("bee", "bee, bees, honey, insect, buzz, buzzing, pollinate, hive, busy, hardworking", "animals")
def _(P):
    x = wave(P.t, 2, 8)
    y = wave(P.t, 3.3, 6, 1)
    fl = math.sin(P.t * 30)
    P.ellipse(46 + x, 34 + y - 4 * fl, 12, 8, w=2.4, fill="white")
    P.ellipse(60 + x, 32 + y - 4 * fl, 12, 8, w=2.4, fill="white")
    P.ellipse(52 + x, 56 + y, 26, 18, w=3.6, fill="yellow")
    for dx in (-8, 4):
        P.line(52 + x + dx, 40 + y, 52 + x + dx + 2, 72 + y, w=4.4, color="black")
    P.dot(72 + x, 52 + y, 2.4)
    P.poly([(26 + x, 56 + y), (16 + x, 58 + y), (26 + x, 62 + y)], w=1.8, fill="black")
    P.stroke([(8 + i * 6, 80 + math.sin(i * 1.2) * 4) for i in range(6)], w=1.6, color="gray")


@prop("dinosaur", "dinosaur, dinosaurs, t rex, extinct, extinction, fossil, fossils, jurassic, prehistoric, millions of years ago", "animals")
def _(P):
    j = abs(math.sin(P.t * 3)) * 4
    P.poly([(8, 70), (30, 54), (40, 34), (52, 22), (72, 20), (88, 28), (88, 40), (72, 42 + j), (70, 50), (60, 54), (62, 74),
            (54, 74), (50, 64), (40, 72), (42, 88), (34, 88), (30, 74)], w=3.6, fill="green", smooth=True)
    P.dot(74, 28, 2.6)
    P.stroke([(74, 40 + j * 0.5), (86, 38)], w=1.8)
    for x in (52, 62, 72):
        P.poly([(x - 3, 22), (x, 14), (x + 3, 22)], w=1.6, fill="darkgreen")


@prop("bat", "bat, bats, vampire, night creature, cave creature, spooky night, dracula", "animals")
def _(P):
    flap = math.sin(P.t * 10)
    by = wave(P.t, 2.5, 4)
    for s in (-1, 1):
        wing = [(50 + s * 8, 44 + by), (50 + s * 24, 30 + by - 10 * flap), (50 + s * 44, 34 + by - 14 * flap),
                (50 + s * 38, 50 + by), (50 + s * 30, 46 + by), (50 + s * 24, 56 + by), (50 + s * 16, 50 + by), (50 + s * 8, 58 + by)]
        P.poly(wing, w=3, fill="black")
    P.ellipse(50, 50 + by, 9, 13, w=3, fill="black")
    P.poly([(44, 40 + by), (42, 30 + by), (48, 38 + by)], w=2, fill="black")
    P.poly([(56, 40 + by), (58, 30 + by), (52, 38 + by)], w=2, fill="black")
    P.dot(46, 46 + by, 1.6, color="yellow")
    P.dot(54, 46 + by, 1.6, color="yellow")


# ============================================================================================ FOOD / HEALTH
@prop("pizza", "pizza, food, italian food, fast food, slice, junk food, dinner, takeout, eat, eating", "food")
def _(P):
    a = wave(P.t, 2, 5)
    P.poly(rot([(50, 88), (14, 20), (86, 20)], 50, 50, a), w=3.6, fill="yellow")
    P.poly(rot([(10, 12), (90, 12), (88, 24), (12, 24)], 50, 50, a), w=3.2, fill="brown", smooth=True)
    for x, y in ((40, 36), (58, 40), (50, 58), (34, 28), (62, 28)):
        P.circle(*rot([(x, y)], 50, 50, a)[0], 5, w=2, fill="red")
    drip = (P.t * 0.8) % 1
    P.curve(rot([(50, 88), (52, 92 + drip * 6)], 50, 50, a), w=2.6, color="yellow")


@prop("burger", "burger, burgers, hamburger, fast food, junk food, cheeseburger, mcdonalds, fries, unhealthy food, lunch", "food")
def _(P):
    b = abs(math.sin(P.t * 3)) * 2
    P.rrect(16, 70, 84, 84, r=6, w=3.4, fill="brown")
    P.stroke([(14, 66), (24, 60), (34, 68), (44, 60), (54, 68), (64, 60), (74, 68), (86, 62)], w=4, color="green")
    P.rrect(14, 56, 86, 66, r=4, w=3.2, fill="brown")
    P.poly([(16, 54), (84, 54), (78, 62), (64, 56), (50, 62), (36, 56), (22, 62)], w=2.6, fill="yellow")
    P.poly([(14, 52 - b), (20, 30 - b), (36, 18 - b), (64, 18 - b), (80, 30 - b), (86, 52 - b)], w=3.6, fill="orange", smooth=True)
    for x, y in ((34, 30), (50, 26), (64, 32), (44, 40)):
        P.ellipse(x, y - b, 2.4, 1.4, w=1.2, fill="cream")


@prop("coffee", "coffee, caffeine, morning coffee, cafe, espresso, latte, tea, hot drink, starbucks, cup of coffee", "food")
def _(P):
    for i in range(3):
        x = 38 + i * 12
        k = (P.t * 0.8 + i * 0.3) % 1
        P.curve([(x, 34 - k * 10), (x + 4, 26 - k * 10), (x - 2, 18 - k * 10), (x + 2, 10 - k * 10)], w=2.2, color="gray")
    P.arc(78, 60, 10, 12, -90, 90, w=4)
    P.poly([(22, 38), (78, 38), (72, 84), (28, 84)], w=3.6, fill="red")
    P.ellipse(50, 38, 28, 5, w=2.6, fill="brown")
    P.ellipse(50, 88, 34, 5, w=3, fill="white")


@prop("apple", "apple, apples, fruit, fruits, healthy, healthy food, diet, nutrition, teacher, vitamins, eat healthy", "food")
def _(P):
    a = wave(P.t, 2, 4)
    P.poly(rot([(50, 30), (66, 20), (82, 26), (88, 46), (82, 72), (66, 88), (50, 84), (34, 88), (18, 72), (12, 46), (18, 26), (34, 20)],
               50, 55, a), w=3.6, fill="red", smooth=True)
    P.stroke(rot([(50, 30), (52, 12)], 50, 55, a), w=3.4, color="brown")
    P.poly(rot([(53, 18), (66, 8), (72, 14), (60, 22)], 50, 55, a), w=2.4, fill="green", smooth=True)
    P.arc(*rot([(32, 46)], 50, 55, a)[0], 8, 12, 150, 230, w=2.4, color="white")


@prop("cake", "cake, birthday, birthday cake, party cake, celebrate, celebration, dessert, sweets, anniversary, candles", "food")
def _(P):
    P.rrect(14, 52, 86, 88, r=4, w=3.4, fill="pink")
    P.stroke([(14, 60), (24, 66), (34, 60), (44, 66), (54, 60), (64, 66), (74, 60), (86, 66)], w=3, color="white")
    P.rrect(24, 32, 76, 52, r=4, w=3.2, fill="cream")
    for x in (36, 50, 64):
        P.rect(x - 2.5, 18, x + 2.5, 32, w=2, fill="blue")
        f = 1 + 0.2 * math.sin(P.t * 12 + x)
        P.poly([(x, 16 - 7 * f), (x + 3, 12), (x, 18), (x - 3, 12)], w=1.6, fill="orange", smooth=True)


@prop("donut", "donut, donuts, doughnut, sweets, sugar, snack, treat, dessert, bakery", "food")
def _(P):
    a = P.t * 20
    P.circle(50, 50, 36, w=3.6, fill="brown")
    P.blob(rot([(18, 50), (24, 26), (44, 16), (66, 20), (82, 36), (80, 60), (70, 78), (50, 84), (30, 76)], 50, 50, a), w=3, fill="pink")
    P.circle(50, 50, 12, w=3, fill="paper")
    for i in range(8):
        x, y = rot([(50 + 22 * math.cos(i * 0.8), 50 + 22 * math.sin(i * 0.8))], 50, 50, a)[0]
        P.line(x - 2, y - 2, x + 2, y + 2, w=2.2, color=("yellow", "blue", "green", "white")[i % 4])


@prop("pill", "medicine, medication, pill, pills, drug, drugs, pharmacy, cure, treatment, prescription, doctor prescribed, side effects", "food")
def _(P):
    a = 35 + wave(P.t, 2, 8)
    P.poly(rot([(30, 38), (50, 38), (50, 62), (30, 62)], 50, 50, a), w=0.1, fill="red")
    P.poly(rot([(50, 38), (70, 38), (70, 62), (50, 62)], 50, 50, a), w=0.1, fill="white")
    pts = []
    for ang in range(90, 271, 15):
        pts.append((30 + 12 * math.cos(math.radians(ang)), 50 + 12 * math.sin(math.radians(ang))))
    for ang in range(-90, 91, 15):
        pts.append((70 + 12 * math.cos(math.radians(ang)), 50 + 12 * math.sin(math.radians(ang))))
    P.poly(rot(pts, 50, 50, a), w=3.4)
    P.stroke(rot([(50, 38), (50, 62)], 50, 50, a), w=2.6)


@prop("syringe", "vaccine, vaccines, vaccination, injection, shot, needle, medical, inject, jab, flu shot, immunization", "food")
def _(P):
    a = -45
    push = abs(math.sin(P.t * 2)) * 8
    P.poly(rot([(22, 42), (66, 42), (66, 58), (22, 58)], 50, 50, a), w=3.4, fill="white")
    P.poly(rot([(30 + push, 44), (64, 44), (64, 56), (30 + push, 56)], 50, 50, a), w=0.1, fill="lightblue")
    P.stroke(rot([(66, 50), (90, 50)], 50, 50, a), w=2.4)
    P.stroke(rot([(8 + push, 50), (22, 50)], 50, 50, a), w=4)
    P.stroke(rot([(8 + push, 40), (8 + push, 60)], 50, 50, a), w=4)
    for x in (34, 44, 54):
        P.stroke(rot([(x, 42), (x, 48)], 50, 50, a), w=1.6)


@prop("hospital", "hospital, doctor, doctors, emergency, medical, health, healthcare, ambulance, nurse, er, clinic, sick, illness, patient", "food")
def _(P):
    k = 1 + 0.06 * math.sin(P.t * 5)
    P.rrect(14, 14, 86, 86, r=12, w=3.6, fill="white")
    P.poly(scale([(40, 22), (60, 22), (60, 40), (78, 40), (78, 60), (60, 60), (60, 78), (40, 78), (40, 60), (22, 60), (22, 40),
                  (40, 40)], 50, 50, k), w=3.2, fill="red")


@prop("bandage", "injury, injured, hurt, wound, heal, healing, bandage, band aid, recovery, recover, pain, accident", "food")
def _(P):
    a = -30 + wave(P.t, 2, 4)
    pts = []
    for ang in range(90, 271, 15):
        pts.append((20 + 14 * math.cos(math.radians(ang)), 50 + 14 * math.sin(math.radians(ang))))
    for ang in range(-90, 91, 15):
        pts.append((80 + 14 * math.cos(math.radians(ang)), 50 + 14 * math.sin(math.radians(ang))))
    P.poly(rot(pts, 50, 50, a), w=3.4, fill="skin")
    P.poly(rot([(38, 38), (62, 38), (62, 62), (38, 62)], 50, 50, a), w=2.6, fill="cream")
    for x, y in ((44, 44), (56, 44), (44, 56), (56, 56), (50, 50)):
        P.dot(*rot([(x, y)], 50, 50, a)[0], 1.4)


@prop("tooth", "dentist, tooth, teeth, smile, dental, brushing, cavity, toothache", "food")
def _(P):
    b = abs(math.sin(P.t * 3)) * 3
    P.poly([(22, 28 - b), (34, 14 - b), (50, 20 - b), (66, 14 - b), (78, 28 - b), (76, 52 - b), (68, 86 - b), (60, 86 - b), (54, 62 - b),
            (46, 62 - b), (40, 86 - b), (32, 86 - b), (24, 52 - b)], w=3.6, fill="white", smooth=True)
    P.arc(38, 38 - b, 2.4, 3, 0, 360, w=2.2)
    P.arc(62, 38 - b, 2.4, 3, 0, 360, w=2.2)
    P.arc(50, 44 - b, 8, 6, 20, 160, w=2.4)
    P.sparkle(84, 16, r=7, phase=0)


# ============================================================================================ TRANSPORT
@prop("car", "car, cars, drive, driving, drove, vehicle, road trip, tesla, driver, traffic, automobile, commute, getaway car", "transport")
def _(P):
    b = abs(math.sin(P.t * 8)) * 1.4
    for i in range(3):
        x = 6 - ((P.t * 40 + i * 10) % 30)
        P.line(x + 4, 58 + i * 7, x - 6, 58 + i * 7, w=2, color="gray")
    P.poly([(10, 66 - b), (14, 50 - b), (30, 46 - b), (40, 30 - b), (66, 30 - b), (78, 46 - b), (90, 50 - b), (92, 66 - b)], w=3.6,
           fill="red")
    P.poly([(44, 34 - b), (62, 34 - b), (70, 46 - b), (40, 46 - b)], w=2.6, fill="lightblue")
    a = P.t * 600
    for x in (28, 74):
        P.circle(x, 68, 10, w=3.4, fill="black")
        P.circle(x, 68, 4, w=1.6, fill="silver")
        r = math.radians(a)
        P.line(x - 7 * math.cos(r), 68 - 7 * math.sin(r), x + 7 * math.cos(r), 68 + 7 * math.sin(r), w=1.4, color="silver")
    P.circle(88, 54 - b, 3, w=1.6, fill="yellow")


@prop("plane", "plane, planes, flight, flights, airplane, aeroplane, travel by air, airport, flew, aviation, pilot, jet, missing flight, mh370", "transport")
def _(P):
    by = wave(P.t, 2, 3)
    a = -8 + wave(P.t, 1.4, 3)
    body = rot([(10, 50), (24, 44), (84, 44), (94, 50), (84, 56), (24, 56)], 50, 50, a)
    P.poly(rot([(44, 50), (66, 50), (40, 82), (30, 82)], 50, 50, a), w=3, fill="lightgray")
    P.poly([(x, y + by) for x, y in body], w=3.6, fill="white", smooth=True)
    P.poly([(x, y + by) for x, y in rot([(44, 48), (66, 48), (40, 18), (30, 18)], 50, 50, a)], w=3, fill="lightgray")
    P.poly([(x, y + by) for x, y in rot([(14, 48), (22, 46), (16, 30), (8, 30)], 50, 50, a)], w=2.6, fill="red")
    for i in range(4):
        x, y = rot([(60 + i * 6, 49)], 50, 50, a)[0]
        P.dot(x, y + by, 1.6, color="blue")


@prop("ship", "ship, ships, boat, boats, sailing, titanic, cruise, voyage, sea travel, shipwreck, sailor, vessel, ghost ship, captain", "transport")
def _(P):
    rock = wave(P.t, 1.8, 4)
    hull = rot([(10, 58), (90, 58), (78, 76), (22, 76)], 50, 66, rock)
    P.poly(hull, w=3.6, fill="brown")
    P.stroke(rot([(50, 58), (50, 12)], 50, 66, rock), w=3.2)
    P.poly(rot([(52, 14), (52, 52), (80, 52)], 50, 66, rock), w=3, fill="white")
    P.poly(rot([(48, 20), (48, 52), (24, 52)], 50, 66, rock), w=3, fill="white")
    P.poly(rot([(50, 12), (62, 15), (50, 18)], 50, 66, rock), w=1.8, fill="red")
    P.stroke([(4 + i * 6, 80 + math.sin(i * 0.9 + P.t * 3) * 3) for i in range(16)], w=2.8, color="blue")


@prop("train", "train, trains, railway, railroad, subway, metro, locomotive, commute by train, station, tracks", "transport")
def _(P):
    sh = wave(P.t, 14, 0.8)
    for i in range(3):
        k = (P.t * 0.8 + i * 0.3) % 1
        P.circle(26 + k * 14, 18 - k * 12, 4 + k * 5, w=2, fill="lightgray")
    P.rect(18 + sh, 24, 34 + sh, 42, w=3, fill="black")
    P.rrect(12 + sh, 40, 66 + sh, 72, r=4, w=3.4, fill="green")
    P.rrect(62 + sh, 26, 90 + sh, 72, r=4, w=3.4, fill="red")
    P.rect(68 + sh, 32, 84 + sh, 46, w=2.4, fill="lightblue")
    P.poly([(6 + sh, 72), (12 + sh, 60), (12 + sh, 72)], w=2.4, fill="gray")
    for x in (24, 46, 76):
        P.circle(x + sh, 76, 7, w=3, fill="black")
    P.line(2, 86, 98, 86, w=2.6)


@prop("bike", "bike, bicycle, cycling, cyclist, ride, riding, pedal, tour de france", "transport")
def _(P):
    a = P.t * 300
    for x in (24, 76):
        P.circle(x, 64, 18, w=3.4)
        for k in range(3):
            r = math.radians(a + k * 60)
            P.line(x - 16 * math.cos(r), 64 - 16 * math.sin(r), x + 16 * math.cos(r), 64 + 16 * math.sin(r), w=1.4)
    P.stroke([(24, 64), (40, 40), (66, 40), (76, 64)], w=3.4, color="red")
    P.stroke([(40, 40), (50, 64), (66, 40)], w=3.4, color="red")
    P.stroke([(36, 32), (46, 32)], w=4)
    P.stroke([(66, 40), (64, 28), (72, 26)], w=3.2)


@prop("helicopter", "helicopter, chopper, rescue helicopter, air rescue, search and rescue, aerial, news helicopter", "transport")
def _(P):
    by = wave(P.t, 2.4, 3)
    sp = math.sin(P.t * 40)
    P.line(50 - 40 * sp, 18 + by, 50 + 40 * sp, 18 + by, w=3.4)
    P.line(50, 18 + by, 50, 28 + by, w=3)
    P.stroke([(70, 44 + by), (92, 40 + by)], w=4)
    P.line(92, 32 + by + 6 * sp, 92, 48 + by - 6 * sp, w=2.6)
    P.ellipse(48, 46 + by, 26, 18, w=3.6, fill="yellow")
    P.poly([(28, 40 + by), (40, 32 + by), (48, 32 + by), (48, 48 + by), (26, 48 + by)], w=2.6, fill="lightblue")
    P.line(30, 72 + by, 70, 72 + by, w=3.4)
    P.line(38, 62 + by, 36, 72 + by, w=2.6)
    P.line(58, 62 + by, 60, 72 + by, w=2.6)


@prop("submarine", "submarine, deep sea, ocean exploration, underwater, sub, titan sub, deep ocean, mariana trench, abyss", "transport")
def _(P):
    by = wave(P.t, 1.6, 3)
    P.ellipse(48, 56 + by, 36, 16, w=3.6, fill="yellow")
    P.rrect(38, 32 + by, 58, 44 + by, r=3, w=3, fill="yellow")
    P.line(50, 32 + by, 50, 20 + by, w=2.6)
    P.line(50, 20 + by, 58, 20 + by, w=2.6)
    for x in (32, 48, 64):
        P.circle(x, 56 + by, 5, w=2.4, fill="lightblue")
    P.poly([(84, 56 + by), (94, 46 + by + wave(P.t, 10, 3)), (94, 66 + by - wave(P.t, 10, 3))], w=2.6, fill="gray")
    for i in range(3):
        k = (P.t * 0.9 + i * 0.33) % 1
        P.circle(90 - k * 20, 50 + by - k * 40, 2 + i, w=1.6)


@prop("bus", "bus, buses, school bus, public transport, transit, travel by bus, tour bus", "transport")
def _(P):
    b = abs(math.sin(P.t * 7)) * 1.2
    P.rrect(8, 26 - b, 92, 74 - b, r=6, w=3.6, fill="yellow")
    for x in (16, 32, 48, 64):
        P.rect(x, 34 - b, x + 12, 48 - b, w=2.4, fill="lightblue")
    P.rect(80, 34 - b, 88, 66 - b, w=2.4, fill="lightblue")
    P.line(8, 56 - b, 92, 56 - b, w=2.2)
    for x in (24, 74):
        P.circle(x, 76, 8, w=3, fill="black")


# ============================================================================================ PLACES / BUILDINGS
@prop("house", "house, houses, home, homes, real estate, rent, mortgage, property, housing, family home, neighborhood, homeowner", "places")
def _(P):
    P.rect(66, 18, 74, 36, w=2.6, fill="red")
    for i in range(3):
        k = (P.t * 0.6 + i * 0.33) % 1
        P.circle(70 + k * 6, 14 - k * 12, 3 + k * 4, w=1.8, fill="lightgray")
    P.poly([(8, 46), (50, 14), (92, 46)], w=3.6, fill="red")
    P.rect(18, 44, 82, 88, w=3.6, fill="cream")
    P.rect(42, 62, 58, 88, w=3, fill="brown")
    P.dot(55, 76, 1.8)
    for x in (24, 62):
        on = int(P.t * 1.5 + x) % 3 != 0
        P.rect(x, 52, x + 14, 64, w=2.6, fill="yellow" if on else "lightblue")


@prop("castle", "castle, castles, kingdom, medieval, fortress, palace, king's castle, middle ages, tower, knights castle", "places")
def _(P):
    for x in (10, 70):
        P.rect(x, 30, x + 20, 90, w=3.4, fill="gray")
        for k in range(3):
            P.rect(x + k * 7, 24, x + k * 7 + 5, 30, w=2.4, fill="gray")
    P.rect(30, 44, 70, 90, w=3.4, fill="lightgray")
    for k in range(5):
        P.rect(30 + k * 8, 38, 30 + k * 8 + 6, 44, w=2.4, fill="lightgray")
    P.poly([(42, 90), (42, 66), (50, 58), (58, 66), (58, 90)], w=3, fill="brown")
    P.line(20, 24, 20, 8, w=2.2)
    pts = [(20, 8)] + [(20 + i * 4, 10 + wave(P.t, 6, 2, -i)) for i in range(1, 4)] + [(32, 16), (20, 16)]
    P.poly(pts, w=2, fill="red")


@prop("pyramid", "pyramid, pyramids, egypt, egyptian, ancient egypt, pharaoh, tomb, giza, mummy, ancient civilization, sphinx", "places")
def _(P):
    P.circle(80, 20, 8 + math.sin(P.t * 2), w=2.6, fill="yellow")
    P.poly([(6, 86), (46, 20), (86, 86)], w=3.6, fill="gold")
    P.poly([(46, 20), (86, 86), (94, 80)], w=3, fill="orange")
    for i in range(1, 5):
        y = 20 + i * 13.2
        P.line(46 - (y - 20) * 0.6, y, 46 + (y - 20) * 0.6, y, w=1.8)
    P.curve([(2, 90), (30, 86), (60, 90), (98, 86)], w=2.6, color="brown")


@prop("city", "city, cities, skyscraper, skyscrapers, downtown, urban, new york, office building, metropolis, tower, buildings, skyline", "places")
def _(P):
    for x, h, c in ((8, 50, "gray"), (24, 72, "blue"), (46, 58, "teal"), (66, 80, "purple"), (84, 44, "gray")):
        P.rect(x, 90 - h, x + 16, 90, w=3, fill=c)
        for r in range(int(h / 12)):
            for cc in range(2):
                on = (r + cc + int(P.t * 2) + x) % 4 != 0
                P.rect(x + 3 + cc * 6, 90 - h + 5 + r * 11, x + 7 + cc * 6, 90 - h + 10 + r * 11, w=1.2,
                       fill="yellow" if on else "white")
    P.line(2, 90, 98, 90, w=3)


@prop("factory", "factory, factories, industry, industrial, manufacturing, pollution, production, plant, made in, assembly line, workers", "places")
def _(P):
    for i, x in enumerate((60, 76)):
        for k in range(3):
            kk = (P.t * 0.6 + k * 0.33 + i * 0.15) % 1
            P.circle(x + 4 + kk * 8, 18 - kk * 16, 3 + kk * 5, w=1.8, fill="gray")
        P.rect(x, 20, x + 8, 50, w=3, fill="red")
    P.poly([(8, 90), (8, 48), (24, 36), (24, 48), (40, 36), (40, 48), (56, 36), (56, 50), (92, 50), (92, 90)], w=3.6, fill="gray")
    for x in (14, 30, 46, 66):
        P.rect(x, 62, x + 10, 72, w=2.2, fill="yellow")


@prop("school", "school, schools, class, classroom, teacher, teachers, education system, kids at school, homework, exam, exams, test", "places")
def _(P):
    P.poly([(10, 40), (50, 16), (90, 40)], w=3.4, fill="red")
    P.rect(16, 40, 84, 88, w=3.6, fill="cream")
    P.rect(44, 64, 56, 88, w=3, fill="brown")
    for x in (22, 64):
        P.rect(x, 48, x + 14, 58, w=2.4, fill="lightblue")
    P.circle(50, 32, 6, w=2.2, fill="white")
    a = math.radians(-90 + P.t * 90)
    P.line(50, 32, 50 + 4 * math.cos(a), 32 + 4 * math.sin(a), w=1.6)
    P.line(50, 16, 50, 6, w=2)
    P.poly([(50, 6), (60 + wave(P.t, 6, 2), 8), (50, 11)], w=1.6, fill="blue")


@prop("lighthouse", "lighthouse, lighthouses, coast, coastal, keeper, lighthouse keeper, beacon, guiding light, flannan isles, shore", "places")
def _(P):
    a = P.t * 2
    for s in (-1, 1):
        ex = 50 + s * 46 * abs(math.cos(a))
        P.poly([(50, 24), (ex, 14), (ex, 34)], w=1.4, fill="yellow")
    P.poly([(36, 88), (40, 32), (60, 32), (64, 88)], w=3.6, fill="white")
    for y in (44, 60, 76):
        P.poly([(40 - (y - 32) * 0.07, y), (60 + (y - 32) * 0.07, y), (60 + (y + 8 - 32) * 0.07, y + 8),
                (40 - (y + 8 - 32) * 0.07, y + 8)], w=1.6, fill="red")
    P.rect(40, 18, 60, 32, w=3, fill="yellow")
    P.poly([(36, 18), (50, 6), (64, 18)], w=3, fill="red")
    P.stroke([(4 + i * 6, 90 + math.sin(i + P.t * 3) * 2) for i in range(16)], w=2.6, color="blue")


@prop("tent", "camping, camp, tent, outdoors, wilderness, survival, campsite, camping trip, woods camping, forest camp", "places")
def _(P):
    P.poly([(8, 86), (50, 18), (92, 86)], w=3.6, fill="green")
    P.poly([(38, 86), (50, 50), (62, 86)], w=3, fill="darkgreen")
    P.line(50, 18, 50, 8, w=2.4)
    for i in range(3):
        x = 82 + i * 4 - 4
        f = 1 + 0.2 * math.sin(P.t * 10 + i)
        P.poly([(x, 86 - 12 * f), (x + 3, 82), (x, 88), (x - 3, 82)], w=1.6, fill="orange")


@prop("island", "island, islands, stranded, remote, remote island, desert island, castaway, deserted island, tropical, paradise, shipwrecked", "places")
def _(P):
    P.ellipse(50, 72, 34, 10, w=3.4, fill="gold")
    sw = wave(P.t, 1.8, 3)
    P.curve([(52, 70), (50, 52), (54 + sw * 0.3, 32)], w=4.4, color="brown")
    for a in (-160, -120, -60, -20):
        r = math.radians(a)
        P.curve([(54 + sw * 0.3, 32), (54 + sw + 14 * math.cos(r), 30 + 10 * math.sin(r) - 4),
                 (54 + sw + 26 * math.cos(r), 34 + 16 * math.sin(r) + 10)], w=4, color="green")
    P.stroke([(4 + i * 6, 82 + math.sin(i + P.t * 3) * 2) for i in range(16)], w=2.6, color="blue")
    P.circle(84, 18, 8, w=2.6, fill="yellow")


@prop("cave", "cave, caves, underground, explore cave, hidden passage, tunnel, tunnels, cavern, dark place, mine, mines", "places")
def _(P):
    P.poly([(4, 90), (10, 46), (30, 20), (56, 14), (80, 24), (94, 52), (96, 90)], w=3.6, fill="gray", smooth=True)
    P.poly([(28, 90), (30, 60), (42, 44), (58, 44), (70, 60), (72, 90)], w=3.2, fill="black", smooth=True)
    blink = int(P.t * 12) % 24 < 2
    if not blink and P.t > 0.8:
        P.dot(46, 66, 2.6, color="yellow")
        P.dot(54, 66, 2.6, color="yellow")


@prop("bridge", "bridge, bridges, connect, connection, cross, crossing, golden gate, river crossing, build bridges, link", "places")
def _(P):
    P.line(4, 66, 96, 66, w=4)
    for x in (24, 76):
        P.rect(x - 4, 22, x + 4, 88, w=3, fill="red")
    P.curve([(4, 30), (24, 22), (50, 56), (76, 22), (96, 30)], w=2.6)
    for x in range(30, 72, 7):
        y = 22 + (34 * math.sin(math.pi * (x - 24) / 52))
        P.line(x, y, x, 66, w=1.4)
    P.stroke([(4 + i * 6, 82 + math.sin(i + P.t * 3) * 2) for i in range(16)], w=2.6, color="blue")
    k = (P.t * 0.4) % 1
    P.rect(4 + k * 84, 58, 14 + k * 84, 65, w=2, fill="yellow")


@prop("haunted_house", "haunted house, abandoned house, abandoned, creepy house, mansion, old mansion, ghost house, derelict, ruins", "places")
def _(P):
    P.circle(80, 16, 9, w=2.6, fill="yellow")
    P.poly([(14, 46), (40, 22), (66, 46)], w=3.4, fill="purple")
    P.rect(20, 46, 60, 88, w=3.4, fill="gray")
    P.poly([(56, 40), (72, 30), (88, 40)], w=3, fill="purple")
    P.rect(60, 40, 84, 88, w=3.2, fill="gray")
    for x, y in ((26, 54), (44, 54), (66, 50)):
        on = int(P.t * 2 + x) % 3 == 0
        P.rect(x, y, x + 10, y + 12, w=2.2, fill="yellow" if on else "black")
    P.rect(34, 70, 46, 88, w=2.6, fill="black")
    P.line(66, 66, 78, 78, w=1.6)
    flap = math.sin(P.t * 10)
    by = wave(P.t, 2, 3)
    P.stroke([(14, 18 + by), (20, 14 + by - 4 * flap), (26, 18 + by), (32, 14 + by - 4 * flap), (38, 18 + by)], w=2.2)


# ================================================================================================ EXTRA
@prop("vote", "vote, votes, voting, voted, election, elections, ballot, ballots, democracy, poll, polls, voter, referendum", "symbols")
def _(P):
    drop = min(1, max(0, (P.t - 0.6) * 1.5))
    P.poly([(40, 6 + 30 * drop), (64, 10 + 30 * drop), (60, 34 + 30 * drop), (36, 30 + 30 * drop)], w=2.6, fill="white")
    P.stroke([(44, 20 + 30 * drop), (48, 25 + 30 * drop), (56, 16 + 30 * drop)], w=2.6, color="green")
    P.rect(16, 40, 84, 90, w=3.6, fill="blue")
    P.rect(12, 36, 88, 44, w=3.2, fill="blue")
    P.line(36, 40, 64, 40, w=3.4, color="black")
    P.star(50, 66, 10, 4.4, w=2.2, fill="white")


@prop("ball", "sports, sport, football, soccer, basketball, game day, athlete, athletes, team, match, goal scored, championship game", "symbols")
def _(P):
    hop = abs(math.sin(P.t * 3.4)) * 26
    sq = 1 - 0.12 * max(0, 1 - hop / 6)
    P.ellipse(50, 90, 18 - hop * 0.3, 3, w=2, fill="lightgray")
    P.ellipse(50, 60 - hop, 26, 26 * sq, w=3.6, fill="orange")
    P.arc(50, 60 - hop, 26, 26 * sq, 0, 360, w=0.1)
    P.line(24, 60 - hop, 76, 60 - hop, w=2.4)
    P.line(50, 34 - hop, 50, 86 - hop, w=2.4)
    P.arc(30, 60 - hop, 12, 22 * sq, -70, 70, w=2.4)
    P.arc(70, 60 - hop, 12, 22 * sq, 110, 250, w=2.4)


@prop("pumpkin", "pumpkin, pumpkins, halloween, halloween night, jack o lantern, autumn, fall, october, trick or treat, spooky season", "symbols")
def _(P):
    glow = int(P.t * 6) % 3 != 0
    for dx, rx in ((-20, 18), (20, 18), (0, 20)):
        P.ellipse(50 + dx, 58, rx, 28, w=3.4, fill="orange")
    P.poly([(46, 30), (48, 14), (56, 12), (54, 30)], w=3, fill="darkgreen")
    for x in (38, 62):
        P.poly([(x - 7, 56), (x, 46), (x + 7, 56)], w=2.2, fill="yellow" if glow else "black")
    P.poly([(32, 68), (40, 74), (46, 68), (54, 74), (60, 68), (68, 74), (62, 80), (38, 80)], w=2.2, fill="yellow" if glow else "black")


@prop("masks", "theater, theatre, drama, acting, masks, disguise, disguised, hidden identity, two faces, double life, secret identity, comedy and tragedy", "symbols")
def _(P):
    a = wave(P.t, 1.5, 5)
    for cx, cy, ang, col, happy in ((36, 46, -14 + a, "yellow", True), (64, 54, 14 - a, "lightblue", False)):
        mask = rot([(cx - 18, cy - 20), (cx + 18, cy - 20), (cx + 20, cy + 4), (cx + 10, cy + 22), (cx - 10, cy + 22), (cx - 20, cy + 4)],
                   cx, cy, ang)
        P.poly(mask, w=3.2, fill=col, smooth=True)
        for ex in (-8, 8):
            P.ellipse(*rot([(cx + ex, cy - 6)], cx, cy, ang)[0], 4, 3, w=2, fill="black")
        if happy:
            P.arc(*rot([(cx, cy + 6)], cx, cy, ang)[0], 10, 7, 20 + ang, 160 + ang, w=2.6)
        else:
            P.arc(*rot([(cx, cy + 16)], cx, cy, ang)[0], 10, 7, 200 + ang, 340 + ang, w=2.6)


@prop("earthquake", "earthquake, earthquakes, quake, tremor, seismic, ground shaking, crack, cracked, fault line, collapse, rubble", "symbols")
def _(P):
    sh = wave(P.t, 28, 2.4)
    P.rect(8 + sh, 50, 92 + sh, 90, w=3.4, fill="brown")
    P.line(8 + sh, 50, 92 + sh, 50, w=3, color="green")
    P.stroke([(50 + sh, 50), (44 + sh, 62), (54 + sh, 70), (46 + sh, 80), (52 + sh, 90)], w=3.6, color="black")
    P.stroke([(44 + sh, 62), (30 + sh, 66)], w=2.4, color="black")
    P.stroke([(54 + sh, 70), (70 + sh, 76)], w=2.4, color="black")
    for x in (20, 80):
        P.rect(x - 8 + sh * 1.6, 26, x + 8 + sh * 1.6, 50, w=3, fill="gray")
        P.rect(x - 4 + sh * 1.6, 32, x + 3 + sh * 1.6, 38, w=1.6, fill="yellow")
    for s in (-1, 1):
        P.line(50 + s * 40, 16, 50 + s * 46, 10, w=2.2, color="orange")


@prop("virus", "virus, viruses, covid, coronavirus, pandemic, epidemic, outbreak, germs, germ, infection, infected, disease, flu, contagious", "symbols")
def _(P):
    a = P.t * 25
    for i in range(10):
        r = math.radians(a + i * 36)
        x1, y1 = 50 + 26 * math.cos(r), 50 + 26 * math.sin(r)
        x2, y2 = 50 + 38 * math.cos(r), 50 + 38 * math.sin(r)
        P.line(x1, y1, x2, y2, w=3)
        P.circle(x2, y2, 4, w=2.2, fill="red")
    P.circle(50, 50, 27, w=3.6, fill="green")
    for x, y in ((40, 42), (58, 40), (52, 60), (38, 58)):
        P.circle(x, y, 4, w=1.8, fill="darkgreen")


@prop("dumbbell", "gym, workout, workouts, weights, lifting, weightlifting, training, fitness goals, exercise routine, bodybuilder", "symbols")
def _(P):
    lift = abs(math.sin(P.t * 2.5)) * 16
    y = 56 - lift
    P.line(26, y, 74, y, w=5)
    for x in (18, 82):
        P.rrect(x - 8, y - 16, x + 8, y + 16, r=3, w=3.2, fill="gray")
    for x in (30, 70):
        P.rrect(x - 4, y - 10, x + 4, y + 10, r=2, w=2.6, fill="gray")


@prop("guitar", "guitar, guitars, rock, rock music, band, musician, concert stage, song writer, singer songwriter, acoustic", "symbols")
def _(P):
    a = wave(P.t, 3, 4)
    body = rot([(26, 58), (34, 50), (44, 52), (50, 60), (58, 62), (64, 72), (58, 86), (40, 90), (22, 86), (16, 74), (20, 64)], 40, 70, a)
    P.stroke(rot([(46, 62), (80, 16)], 40, 70, a), w=5.4, color="brown")
    P.poly(rot([(76, 18), (82, 6), (90, 10), (84, 22)], 40, 70, a), w=2.6, fill="brown")
    P.poly(body, w=3.4, fill="orange", smooth=True)
    P.circle(*rot([(40, 70)], 40, 70, a)[0], 6, w=2.4, fill="black")
    P.stroke(rot([(30, 80), (36, 84)], 40, 70, a), w=3.4)
    for k in (-1.3, 0, 1.3):
        P.stroke(rot([(34 + k, 80 + k), (80 + k, 16 + k)], 40, 70, a), w=0.9, color="white")
    if int(P.t * 3) % 2 == 0:
        P.text(82, 60, "\u266a", size=16, color="purple")


@prop("chain", "chain, chains, chained, trapped, bound, prisoner chained, link, linked, connected, slavery, locked in", "symbols")
def _(P):
    for i in range(5):
        x = 14 + i * 18
        y = 50 + math.sin(i * 0.9 + P.t * 2) * 4
        rx, ry = (12, 7) if i % 2 else (7, 12)
        P.ellipse(x, y, rx, ry, w=4.4)
        P.ellipse(x, y, rx - 2.4, ry - 2.4, w=1.6, color="silver")
