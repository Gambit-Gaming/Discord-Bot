# -*- coding: utf-8 -*-
import asyncio
import json
import logging
from collections import namedtuple
from typing import Optional

import discord
from redbot.core import checks, Config, commands, bot

log = logging.getLogger("red.cogs.bio")

__all__ = ["UNIQUE_ID", "Bio"]

UNIQUE_ID = 0x62696F68617A617264


class Bio(commands.Cog):
    def __init__(self, bot: bot.Red):
        self.bot = bot
        self.conf = Config.get_conf(self, identifier=UNIQUE_ID, force_registration=True)
        self.conf.register_user(bio='{}')
        self.conf.register_guild(biofields='{"fields": []}')

    @commands.command()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_guild=True)
    async def biofields(self, ctx: commands.Context, command: str = None, *args):
        bioFields = json.loads(await self.conf.guild(ctx.guild).biofields())
        if not command:
            await ctx.send("Bio fields available:\n" + \
                           "\n".join(bioFields["fields"]))
            return
        argField = " ".join(args)
        if command == "add":
            bioFields["fields"].append(argField)
        elif command == "remove":
            try:
                bioFields["fields"].remove(argField)
            except:
                await ctx.send(f"No field named '{argField}'")
                return
        else:
            await ctx.send(f"Unknown command: {command}")
        await self.conf.guild(ctx.guild).biofields.set(json.dumps(bioFields))
        await ctx.send(f"Field '{argField}' has been {command[0:5]}ed")
        if command == "remove":
            count = 0
            for member, conf in (await self.conf.all_users()).items():
                memberBio = json.loads(conf.get("bio"))
                if argField in memberBio.keys():
                    del memberBio[argField]
                    await self.conf.user(self.bot.get_user(member)).bio.set(json.dumps(memberBio))
                    count += 1
            await ctx.send(f"Removed field '{argField}' from {count} bios")

    @commands.command()
    @commands.guild_only()
    async def bio(self, ctx: commands.Context, user: Optional[discord.Member] = None, *args):
        bioFields = json.loads(await self.conf.guild(ctx.guild).biofields())
        key = None
        if not isinstance(user, discord.Member):
            # Argument is a key to set, not a user
            if user:
                key = user
                user = None
        _user = user or ctx.author
        bioDict = json.loads(await self.conf.user(_user).bio())

        # User is setting own bio
        if key is not None and _user == ctx.author:
            if key not in bioFields["fields"]:
                await ctx.send("Sorry, that bio field is not available.\n"
                               "Please request it from the server owner.")
                return
            if args:
                bioDict[key] = " ".join(args)
                await self.conf.user(_user).bio.set(json.dumps(bioDict))
                await ctx.send(f"{key} set to {bioDict[key]}")
            else:
                try:
                    del bioDict[key]
                except KeyError:
                    await ctx.send(f"Field '{key}' not found in your bio")
                    return
                await self.conf.user(_user).bio.set(json.dumps(bioDict))
                await ctx.send(f"Field '{key}' removed from bio")
            return

        # Filter dict to key(s)
        elif user and len(args):
            data = {}
            for arg in args:
                try:
                    data[arg] = bioDict[arg]
                except:
                    await ctx.send(f"Field '{arg}' not found")
            bioDict = data
        embed = discord.Embed()
        embed.title = f"{_user}'s Bio"
        embed.set_thumbnail(url=_user.avatar_url)
        for field, value in bioDict.items():
            embed.add_field(name=field, value=value)
        await ctx.send(embed=embed)
