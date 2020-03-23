# -*- coding: utf-8 -*-
import asyncio
import json
import logging
from collections import namedtuple
from typing import Optional

import discord
from redbot.core import Config, commands, bot

log = logging.getLogger("red.cogs.bio")

__all__ = ["UNIQUE_ID", "Bio"]

UNIQUE_ID = 0x62696F68617A617264
MemberBio = namedtuple("MemberBio", "bio")


class Bio(commands.Cog):
    def __init__(self, bot: bot.Red):
        self.conf = Config.get_conf(self, identifier=UNIQUE_ID, force_registration=True)
        self.conf.register_user(bio="{}")

    @commands.command()
    async def bio(self, ctx: commands.Context, user = None, *args):
        key = None
        if not isinstance(user, discord.Member):
            if user and args:
                # Argument is a key to set, not a user
                key = user
            user = ctx.author
        bioDict = json.loads(await self.conf.user(user).bio())
        if key and args:
            bioDict[key] = " ".join(args)
            await self.conf.user(user).bio.set(json.dumps(bioDict))
        else:
            await ctx.send(f"{bioDict}")
