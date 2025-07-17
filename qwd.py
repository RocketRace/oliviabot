import aiosqlite
import discord
from discord.ext import commands

import re
from typing import Any, Callable

from bot import OliviaBot, Context

def qwd_only():
    async def predicate(ctx: Context) -> bool:
        if ctx.author.id in ctx.bot.owner_ids:
            return True
        if ctx.guild and ctx.guild.id == ctx.bot.qwd_id:
            return True
        raise NotQwd

    return commands.check(predicate)


def louna_only():
    async def predicate(ctx: Context) -> bool:
        if ctx.author.id != ctx.bot.louna_id:
            raise NotLouna
        return True
    return commands.check(predicate)

class NotQwd(commands.CheckFailure):
    pass

class NotLouna(commands.CheckFailure):
    pass

AnyUser = discord.User | discord.Member | discord.ClientUser

class QwdieConverter(commands.Converter[AnyUser]):
    def try_find_user(self, bot: OliviaBot, key, mapper: Callable[[discord.User], Any]):
        return discord.utils.find(
            lambda user: mapper(user) == key,
            bot.users
        )

    async def convert(self, ctx: commands.Context[OliviaBot], argument: str):
        choices: list[AnyUser | None] = []
        # id, mention and username are all unique
        if re.match(r"[0-9]{15,20}", argument):
            choices.append(ctx.bot.get_user(int(argument)))
        mention_match = re.match(r"<@!?([0-9]{15,20})>$", argument)
        if mention_match:
            choices.append(ctx.bot.get_user(int(mention_match.group(1))))
        discrim_match = re.match(r"(.+)#([0-9]{4})", argument)
        if discrim_match:
            choices.append(discord.utils.get(
                ctx.bot.users,
                name=discrim_match.group(1),
                discriminator=discrim_match.group(2)
            ))
        # okay technically the username is nonunique because bots still don't have pomelo
        choices.extend([
            user for user in ctx.bot.users
            if user.name.casefold() == argument.casefold()
        ])
        # global name and guild nickname are not unique, so scan all the options
        # this may change later for performance purposes but I only have 100ish users
        choices.extend([
            user for user in ctx.bot.users
            if user.global_name and user.global_name.casefold() == argument.casefold()
        ])
        if ctx.guild:
            choices.extend([
                member for member in ctx.guild.members
                if member.nick and member.nick.casefold() == argument.casefold()
            ])
        # aliases -- casefolded comparison
        choices.extend(ctx.bot.get_user(id) for alias, ids in ctx.bot.person_aliases.items() for id in ids if alias.casefold() == argument.casefold())
        # special results
        if argument == "🪟" or argument.casefold().rstrip("e").startswith("m"):
            choices.append(ctx.author)
        everyone = ""
        if argument in ("@everyone", "🪩"):
            everyone = " (you have to pick one sorry)"
            if ctx.guild:
                choices.extend(ctx.guild.members)
            else:
                choices.extend([ctx.author, ctx.me])
        # finally resolve the user
        valid_choices = list(set(filter(None, choices)))
        if len(valid_choices) == 1:
            return valid_choices[0]
        elif len(valid_choices) >= 2:
            # disambiguate between choices
            valid_choices = sorted(valid_choices, key=lambda user: str(user).casefold())
            content = f"which {argument}?{everyone}"
            view = QwdieDisambiguator(
                target=ctx.author,
                choices=valid_choices,
                whole_guild=set(valid_choices) == set(ctx.guild and ctx.guild.members or [ctx.author, ctx.me])
            )
            msg = await ctx.send(content, view=view)
            await view.wait()
            if view.selected is None:
                for child in view.children:
                    assert isinstance(child, (QwdieButton, QwdieSelect, QwdieUserSelect))
                    child.disabled = True
                await msg.edit(view=view)
                raise TimeoutError
            else:
                return view.selected
        else:
            raise commands.UserNotFound(argument)

class QwdieButton(discord.ui.Button['QwdieDisambiguator']):
    def __init__(self, user: AnyUser):
        # A bit kludgey
        super().__init__(style=discord.ButtonStyle.gray, label=f"@{user}")
        self.user = user
    
    async def callback(self, interaction: discord.Interaction):
        assert self.view
        view: QwdieDisambiguator = self.view
        view.selected = self.user
        for child in view.children:
            assert isinstance(child, QwdieButton)
            child.disabled = True
        self.style = discord.ButtonStyle.green
        await interaction.response.edit_message(view=view)
        view.stop()

def first_difference_at(a: str, b: str) -> int:
    i = 0
    for i, (x, y) in enumerate(zip(a, b)):
        # technically can cause issues due to unicode case folding
        if x.casefold() != y.casefold():
            return i
    return i + 1

class QwdieSelect(discord.ui.Select['QwdieDisambiguator']):
    def __init__(
            self,
            previous: AnyUser | None,
            users: list[AnyUser],
            next: AnyUser | None
        ):
        # when previous is None, users is 25 long
        # when next is None, users may be as short as 1 long
        start = str(users[0])[
            :first_difference_at(
                *(str(users[0]), str(users[1]))
                if previous is None
                else (str(previous), str(users[0]))
            ) + 1
        ]
        if len(users) > 1:
            end = str(users[-1])[
                :first_difference_at(
                    *(str(users[-2]), str(users[-1]))
                    if next is None else
                    (str(users[-1]), str(next))
                ) + 1
            ]
            placeholder = f"Select ({start.upper()} –- {end.upper()})"
        else:
            placeholder = f"Select ({start.upper()})"
        super().__init__(
            placeholder=placeholder,
            options=[
                discord.SelectOption(label=f"@{user}", value=str(i))
                for i, user in enumerate(users)
            ]
        )
        self.users = users
    
    async def callback(self, interaction: discord.Interaction):
        assert self.view
        view: QwdieDisambiguator = self.view
        view.selected = self.users[int(self.values[0])]
        for child in view.children:
            assert isinstance(child, QwdieSelect)
            child.disabled = True
        self.placeholder = f"@{view.selected}"
        await interaction.response.edit_message(view=view)
        view.stop()

class QwdieUserSelect(discord.ui.UserSelect['QwdieDisambiguator']):
    def __init__(self) -> None:
        super().__init__(placeholder = "Select user")

    async def callback(self, interaction: discord.Interaction):
        assert self.view
        view: QwdieDisambiguator = self.view
        view.selected = self.values[0]
        self.placeholder = f"@{view.selected}"
        self.disabled = True
        await interaction.response.edit_message(view=view)
        view.stop()

class QwdieDisambiguator(discord.ui.View):
    def __init__(self, *, target: AnyUser, choices: list[AnyUser], whole_guild: bool):
        super().__init__()
        self.target = target
        self.selected: AnyUser | None = None
        self.msg: discord.Message
        if whole_guild:
            self.add_item(QwdieUserSelect())
        elif len(choices) <= 25:
            for choice in choices:
                self.add_item(QwdieButton(choice))
        elif len(choices) <= 125:
            max = len(choices)
            for i in range(0, max, 25):
                self.add_item(QwdieSelect(
                    choices[i - 1] if i != 0 else None,
                    choices[i : i + 25],
                    choices[i + 25] if i + 25 < max else None
                ))
        else:
            raise RuntimeError("i don't know what to do here")

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user != self.target:
            await interaction.response.send_message("not for you!", ephemeral=True)
            return False
        else:
            return True
