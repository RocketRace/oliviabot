from typing import Literal, NamedTuple
import git

repo = git.Repo(".")
assert not repo.bare


class Change(NamedTuple):
    path: str
    mode: Literal["load", "reload", "unload"]


changes: list[Change] = []

head_commit = repo.head.commit
for diff in head_commit.diff("HEAD~1"):
    diff: git.Diff
    a = diff.a_path
    b = diff.b_path
    if a is None and b is not None:
        changes.append(Change(b, "load"))
    elif b is None and a is not None:
        changes.append(Change(a, "unload"))
    elif a is not None and b is not None:
        if a == b:
            changes.append(Change(a, "reload"))
        else:
            changes.append(Change(a, "unload"))
            changes.append(Change(b, "load"))

is_important = lambda path: (
    path.startswith("data/")
    or path.startswith("scripts/")
    or path.endswith(".py")
    or path.endswith(".pyi")
    or path == "poetry.lock"
    or path == "pypoetry.toml"
)
actionable: list[Change] = list(filter(is_important, changes))
cog_only = all(change.path.startswith("cogs/") for change in actionable)

if actionable and not cog_only:
    print("bot", end="")

elif actionable and cog_only:
    print(";".join(f"{change.mode} {change.path}" for change in actionable))
