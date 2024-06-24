from collections import Counter
import re
import subprocess
import requests
import datetime
import colour
import math
import csv

# === scrape distro list (and hardcode a few) ===
print("generating neofetch logos...")
src = requests.get("https://raw.githubusercontent.com/hykilpikonna/hyfetch/master/neofetch").text
src = src.replace("|\\\n", "|")
start = src.splitlines().index("get_distro_ascii() {")
end = src.splitlines()[start:].index("    esac") + start
matches = src.splitlines()[start:end]

p = "# Flag:    --ascii_distro\n#\n# NOTE: "
distro_start = src.index(p) + len(p)
distro_end = src[distro_start:].index("have ascii logos.") + distro_start
distro_block = src[distro_start:distro_end].strip()
distros = distro_block.replace("#", "").replace("\n", "").split(", ")
kernel_names = [
    # hardcoded kernel names
    "BSD", "Darwin", "GNU", "Linux", "Profelis SambaBOX", "SunOS"
]
distros = sorted(list(set(distros + kernel_names)))

# === scrape pattern list ===
def branching(b: str):
    s = b.strip()
    start, end = s.startswith("*"), s.endswith("*")
    s = s.removeprefix("*").removesuffix("*").removeprefix('"').removesuffix('"').removeprefix("'").removesuffix("'")
    s = re.escape(s)
    if not start:
        s = "^" + s
    if not end:
        s = s + "$"
    return s

pattern_pattern = re.compile(r"""\s*(\*?([a-zA-Z]+|"[^"]+"|'[^']+')\*?)(\s*\|\s*\*?([a-zA-Z_-]+|"[^"]+"|'[^']+')\*?)*\)""", re.IGNORECASE)
raw_patterns = [
    re.compile("|".join([
        branching(branch)
        for branch in line[:-1].strip().split("|")
    ]), re.IGNORECASE)
    for line in matches if pattern_pattern.fullmatch(line)
]

# === append matching distro + suffix to each pattern ===
maybe_with_distros: list[tuple[str, str, str] | None] = [None] * len(raw_patterns)
suffixes = ["_old", "_small", ""]
for distro in distros:
    # nonempty suffixes first
    for suffix in suffixes:
        for i, pattern in enumerate(raw_patterns):
            if pattern.match(f"{distro}{suffix}"):
                maybe_with_distros[i] = (distro, suffix, pattern.pattern)
                # find only the first pattern that matches our input
                break
# there may be orphan patterns
with_distros: list[tuple[str, str, str]] = [row for row in maybe_with_distros if row]

# === append ascii logos & mobile width to each pattern ===
maybe_with_logos: list[tuple[str, str, str, str, int] | None] = [None] * len(raw_patterns)
procs: list[tuple[int, subprocess.Popen[str]]] = []
for i, (distro, suffix, _) in enumerate(with_distros):
    proc = subprocess.Popen(["neowofetch", "--logo", "--stdout=off", "--ascii_distro", distro + suffix], text=True, stdout=subprocess.PIPE)
    procs.append((i, proc))

ansi_pattern = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

for i, proc in procs:
    proc.wait()
    if not proc.stdout: continue
    stdout = proc.stdout.read()
    empty = ansi_pattern.sub("", stdout)
    end = len(empty.rstrip().splitlines())
    start = end - len(empty.strip().splitlines())
    width = max(len(line.rstrip()) for line in empty.splitlines())
    # sqlite bools are 0|1
    mobile_width = int(width < 30)
    # these escapes disable cursor and enable wraparound mode
    partial = stdout.removeprefix("\x1b[?25l\x1b[?7l")
    # remove cleanup lines from the end, as well as blank lines from the beginning
    term_logo = "\n".join(line for line in partial.splitlines()[start:end]).lstrip("\n")
    maybe_with_logos[i] = distro, suffix, *_ = with_distros[i] + (term_logo, mobile_width)
    print(f"{i}/{len(with_distros)}: {distro}{suffix}")

with_logos = [x for x in maybe_with_logos if x is not None]

# === sanitize escapes to the set that discord allows ===
escapes: set[str] = set()
for _, _, _, logo, _ in with_logos:
    escapes = escapes | set(re.findall(ansi_pattern, logo))

discord_colors = {
    None: (185, 187, 190),
    30: (79, 82, 90),
    31: (201, 65, 55),
    32: (136, 152, 45),
    33: (175, 139, 45),
    34: (69, 136, 204),
    35: (195, 68, 130),
    36: (80, 158, 152),
    37: (255, 255, 255),
}

def closest_color(r: int, g: int, b: int):
    def distance(item: tuple[int | None, tuple[int, int, int]]):
        x = colour.XYZ_to_Oklab(colour.sRGB_to_XYZ([r, g, b]))
        y = colour.XYZ_to_Oklab(colour.sRGB_to_XYZ(item[1]))
        return math.dist(x, y)
    return min(discord_colors.items(), key=distance)[0]

def escaper(st: str):
    s = list(map(int, filter(bool, st[2:-1].split(";"))))
    out: list[int | None] = []
    while s:
        code = s.pop(0)
        match code:
            case 38:
                if not s: break
                kind = s.pop(0)
                match kind:
                    case 2:
                        if len(s) < 3: break
                        r, g, b = s.pop(0), s.pop(0), s.pop(0)
                        out.append(closest_color(r, g, b))
                    case 5:
                        if not s: break
                        n = s.pop(0)
                        match n:
                            case 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7:
                                out.append(n + 30)
                            case 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15:
                                out.append(n + 22)
                            case _:
                                if n <= 231:
                                    b = (n - 16) % 6
                                    g = (n - 16) // 6 % 6
                                    r = (n - 16) // 36
                                else:
                                    # close enough
                                    r = g = b = (n - 232) * 10
                                out.append(closest_color(r, g, b))
                    case _: pass
            case 0 | 1 | 4:
                out.append(code)
            case 30 | 31 | 32 | 33 | 34 | 35 | 36 | 37:
                out.append(code)
            case 90 | 91 | 92 | 93 | 94 | 95 | 96 | 97:
                out.append(code - 60)
            case other:
                print("unknown code", other, s)
    return [n for n in out if n is not None]

def unescaper(s: list[int]):
    return f"\x1b[{";".join(map(str, s))}m"

discorder = {escape: unescaper(escaper(escape)) for escape in escapes if escaper(escape)}

for i, (distro, suffix, pattern, logo, mobile_width) in enumerate(with_logos):
    def subber(match: re.Match[str]):
        return discorder.get(match.group(0), "")
    with_logos[i] = distro, suffix, pattern, re.sub(ansi_pattern, subber, logo).replace('`', "`\u200b"), mobile_width

# === append most frequent color (aside from None) to row ===
with_colors: list[tuple[str, str, str, int, int, str, str]] = []
for distro, suffix, pattern, logo, mobile_width in with_logos:
    pat = re.compile(r"\x1b\[(\d+)m")
    escape_spans: list[tuple[int, int]] = []
    color_changes: list[tuple[int, int | None]] = []
    
    for match in pat.finditer(logo):
        start, end = match.span()
        escape_spans.append((start, end))
        color = int(match.group(1))
        if color in discord_colors:
            color_changes.append((start, color))
        elif color == 0:
            color_changes.append((start, None))
    
    logo_colors: list[int | None] = [None for _ in logo]
    for pos, color in color_changes:
        for i in range(pos, len(logo_colors)):
            logo_colors[i] = color
    
    chars = list(logo)
    for start, end in reversed(escape_spans):
        chars[start:end] = logo_colors[start:end] = []

    counter: Counter[int] = Counter()
    color_filter = [color for c, color in zip(chars, logo_colors) 
                    if not c.isspace() and color is not None]
    counter.update(color_filter)
    top = counter.most_common(3)
    # skip black and white if possible, but prefer white
    match top:
        case [[30, _], [37, _], _] | [[37, _], [30, _], _]:
            # third option available, skip black and white
            top = top[2:]
        case [[30, _], *_]:
            # second option available, skip black
            top = top[1:]
        case [[37, _], [30, _]]:
            # don't skip white for black
            pass
        case [[37, _], *_]:
            # skip white for anything else
            top = top[1:]
        case _: pass
    if len(top) == 2 and top[0][0] == 30: 
        top = top[1:]
    
    if top:
        index = top[0][0]
        rgb = bytes(discord_colors[index]).hex()
        with_colors.append((distro, suffix, pattern, mobile_width, index, rgb, logo))
    else:
        with_colors.append((distro, suffix, pattern, mobile_width, 37, "ffffff", logo))

# === push changes to data/ directory ===
with open("data/neofetch_updated", "w") as f:
    now = int(datetime.datetime.now(datetime.UTC).timestamp())
    f.write(f"{now}\n")

with open("data/neofetch.csv", "w") as f:
    writer = csv.writer(f)
    writer.writerow(["distro", "suffix", "pattern", "mobile_width", "color_index", "color_rgb", "logo"])
    writer.writerows(with_colors)
