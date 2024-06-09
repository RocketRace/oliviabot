#!/usr/bin/env python3
# requirements: requests, hyfetch, rust, colour-science, matplotlib (optional)
import re
import subprocess
import requests
import datetime
import colour
import math
import pathlib

logos = {}
variants = {}
patterns = []

# scrape distro list
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
    # kernel name
    "BSD", "Darwin", "GNU", "Linux", "Profelis SambaBOX", "SunOS"
]
distros = sorted(list(set(distros + kernel_names)))
# scrape pattern list
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

matchers = {}
for distro in distros:
    for suffix in ["_old", "_small", ""]:
        matched = False
        for i, opt in enumerate(raw_patterns):
            if matched: break
            if opt.match(f"{distro}{suffix}"):
                matchers[distro, suffix] = opt.pattern
                matched = True

for distro in distros:
    if matchers[distro, ""] == matchers.get((distro, "_old")):
        matchers.pop((distro, "_old"))
    if matchers[distro, ""] == matchers.get((distro, "_small")):
        matchers.pop((distro, "_small"))

# list of supported variants for each distro
for (distro, variant) in matchers:
    variants.setdefault(variant, []).append(distro)

# the distro that each pattern maps to
for pattern in raw_patterns:
    for suffix, distros in variants.items():
        for distro in distros:
            if pattern.match(f"{distro}{suffix}"):
                patterns.append((pattern.pattern, distro, suffix))
                break

# determine ascii logo (more reliable to just ask *fetch directly)
ansi_pattern = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

# spawn a few hundred processes in parallel
# I get about a 6x speedup which is not bad for 10 cores and zero effort
procs = []
for i, distro in enumerate(matchers):
    full_distro = distro[0] + distro[1]
    proc = subprocess.Popen(["neowofetch", "--logo", "--stdout=off", "--ascii_distro", full_distro], text=True, stdout=subprocess.PIPE)
    procs.append((i, full_distro, proc))

mobile_variants = {}
for i, full_distro, proc in procs:
    proc.wait()
    stdout = proc.stdout.read()
    empty = ansi_pattern.sub("", stdout)
    end = len(empty.rstrip().splitlines())
    start = end - len(empty.strip().splitlines())
    width = max(len(line.rstrip()) for line in empty.splitlines())

    if width <= 30:
        for suffix in ["_small", "_old", ""]:
            if full_distro.endswith(suffix):
                mobile_variants.setdefault(suffix, []).append(full_distro.removesuffix(suffix))

    # these escapes disable cursor and enable wraparound mode
    partial = stdout.removeprefix("\x1b[?25l\x1b[?7l")
    # remove cleanup lines from the end, as well as blank lines from the beginning
    logos[full_distro] = "\n".join(line for line in partial.splitlines()[start:end]).lstrip("\n")
    print(f"{i}/{len(matchers)}: {full_distro}")


# sanitize escapes to the set that discord allows
escapes = set()
for logo in logos.values():
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
    out = []
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
            case 0 | 1 | 4:
                out.append(code)
            case 30 | 31 | 32 | 33 | 34 | 35 | 36 | 37:
                out.append(code)
            case 90 | 91 | 92 | 93 | 94 | 95 | 96 | 97:
                out.append(code - 60)
            case other:
                print("unknown code", other, s)
    out = [n for n in out if n is not None]
    return out

unescaper = lambda s: f"\x1b[{";".join(map(str, s))}m"

discorder = {escape: unescaper(escaper(escape)) for escape in escapes if escaper(escape)}

for distro, logo in logos.items():
    def subber(match: re.Match):
        return discorder.get(match.group(0), "")
    logos[distro] = re.sub(ansi_pattern, subber, logo).replace('`', "`\u200b")


with open("src/data/neofetch.rs", "w") as f:
    pathname = pathlib.Path(__file__).relative_to(pathlib.Path.cwd())
    f.write(f"//! @generated by `{pathname}`.\n")
    f.write(f"//! Please do not edit this manually.\n")
    f.write(f"#![allow(clippy::invisible_characters)]\n")
    f.write(f"use regex::Regex;\n")
    f.write(f"use std::collections::HashMap;\n")
    
    now = int(datetime.datetime.now(datetime.UTC).timestamp())
    f.write(f'pub const LAST_UPDATED_POSIX: i64 = {now};\n')

    rust_string = lambda s: '"' + s.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n") + '"'

    def suffix_enum(s):
        match s:
            case "": return "Variant::Standard"
            case "_old": return "Variant::Old"
            case "_small": return "Variant::Small"

    f.write("#[derive(PartialEq, Eq, Hash)] pub enum Variant { Old, Small, Standard }\n")

    # for flagged access
    variant_list = ', '.join(f"({suffix_enum(variant)}, vec![{', '.join(rust_string(distro) for distro in distros)}])"
                             for variant, distros in variants.items())
    f.write(f"pub fn variants() -> HashMap<Variant, Vec<&'static str>> {{ HashMap::from([{variant_list}]) }}\n")
    mobile_variant_list = ', '.join(f"({suffix_enum(variant)}, vec![{', '.join(rust_string(distro) for distro in distros)}])"
                             for variant, distros in mobile_variants.items())
    f.write(f"pub fn mobile_variants() -> HashMap<Variant, Vec<&'static str>> {{ HashMap::from([{mobile_variant_list}]) }}\n")
    
    # for random sampling
    flat_distros = [distro for distros in variants.values() for distro in distros]
    f.write(f"pub const DISTROS: [&str; {len(flat_distros)}] = [{', '.join(
        rust_string(distro) for distro in flat_distros)}];\n")
    flat_mobile_distros = [distro for distros in mobile_variants.values() for distro in distros]
    f.write(f"pub const MOBILE_DISTROS: [&str; {len(flat_mobile_distros)}] = [{', '.join(
        rust_string(distro) for distro in flat_mobile_distros)}];\n")

    pattern_list = ', '.join(f"(Regex::new({rust_string(pattern)}).unwrap(), {rust_string(distro)}, {suffix_enum(suffix)})"
                             for pattern, distro, suffix in patterns)
    f.write(f"pub fn patterns() -> [(Regex, &'static str, Variant); {len(patterns)}] {{ [{pattern_list}] }}\n")

    logo_list = ', '.join(f"({rust_string(name)}, {rust_string(logo)})" for name, logo in logos.items())
    f.write(f"pub fn logos() -> HashMap<&'static str, &'static str> {{ HashMap::from([{logo_list}]) }}\n")
