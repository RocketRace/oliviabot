from collections import namedtuple
import pathlib

import git

repo = git.Repo(".")
assert not repo.bare

Change = namedtuple("Change", "path mode")

# fetch changes
repo.remote().fetch()

# compute touched files
local_head = repo.head.commit
remote_head: git.Commit = repo.remote().refs["main"].commit
changes: list[Change] = []
for item in local_head.diff(remote_head):
    item: git.Diff
    match item.change_type:
        case "A":
            changes.append(Change(item.a_path or "", "load"))
        case "D":
            changes.append(Change(item.a_path or "", "unload"))
        case "M":
            changes.append(Change(item.a_path or "", "reload"))
        case "R":
            changes.append(Change(item.a_path or "", "unload"))
            changes.append(Change(item.b_path or "", "load"))

# pull changes
repo.remote().pull()

# determine whether changes were significant
is_important = lambda change: (
    change.path.startswith("data/")
    or change.path.startswith("scripts/")
    or change.path.endswith(".py")
    or change.path.endswith(".pyi")
    or change.path == "poetry.lock"
    or change.path == "pypoetry.toml"
)
actionable: list[Change] = list(filter(is_important, changes))
cog_only = all(change.path.startswith("cogs/") for change in actionable)
dependencies = any(change.path == "poetry.lock" for change in actionable)

if actionable:
    if dependencies:
        print("dependencies", end="")
    elif cog_only:
        print("cogs", end="")
        with open(".extensions", "w") as f:
            f.writelines(
                f"{change.mode}:cogs.{pathlib.Path(change.path).stem}"
                for change in actionable
            )
    else:
        print("bot", end="")
