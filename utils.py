def dedent(s: str) -> str:
    """textwrap.dedent behaves unexpectedly"""

    tucked = False
    if s.startswith("\n"):
        s = s[1:]
        tucked = True

    lines = s.splitlines()

    if not lines:
        return ""

    def width(line: str) -> int:
        width = 0
        while line[width:].startswith(" "):
            width += 1
        return width

    widths = [width(line) for line in lines]

    if widths[0] == 0 and not tucked:
        common_width = min(widths[1:])
        return "\n".join([lines[0], *[line[common_width:] for line in lines[1:]]])
    else:
        common_width = min(widths)
        return "\n".join(line[common_width:] for line in lines)
