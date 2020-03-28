# -*- coding: utf-8 -*-
import asyncio
import datetime
import time
import hashlib
import logging

import aiohttp
import discord
import feedparser

from typing import Optional

from redbot.core import Config, bot, checks, commands

log = logging.getLogger("red.cogs.tube")

__all__ = ["UNIQUE_ID", "Tube"]

UNIQUE_ID = 0x547562756c6172


class Tube(commands.Cog):
    def __init__(self, bot: bot.Red):
        """A YouTube subscription cog
        
        Thanks to mikeshardmind(Sinbad) for the RSS cog as reference"""
        self.bot = bot
        self.conf = Config.get_conf(self, identifier=UNIQUE_ID, force_registration=True)
        self.conf.register_guild(subscriptions=[])
        self.conf.register_global(interval=300)
        self.session = aiohttp.ClientSession()
        self.bg_loop_task: Optional[asyncio.Task] = None

    def init(self):
        self.bg_loop_task = asyncio.create_task(self.bg_loop())

        def done_callback(future: asyncio.Future):
            try:
                future.exception()
            except asyncio.CancelledError:
                pass
            except asyncio.InvalidStateError as e:
                log.exception("Callback state invalid: ", exc_info=e)
            except Exception as e:
                log.exception("Unexpected exception in rss: ", exc_info=e)

        self.bg_loop_task.add_done_callback(done_callback)

    @commands.guild_only()
    @commands.group()
    async def tube(self, ctx: commands.Context):
        """Post when new videos are added to a YouTube channel"""
        pass

    @checks.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    @tube.command()
    async def subscribe(self, ctx: commands.Context, channelYouTube, channelDiscord: discord.TextChannel = None):
        """Subscribe a Discord channel to a YouTube channel
        
        If no discord channel is specified, the current channel will be subscribed"""
        if not channelDiscord:
            channelDiscord = ctx.channel
        subs = await self.conf.guild(ctx.guild).subscriptions()
        newSub = {'id': channelYouTube,
                  'channel': {"name": channelDiscord.name,
                              "id": channelDiscord.id}}
        newSub['uid'] = self.sub_uid(newSub)
        for sub in subs:
            if sub['uid'] == newSub['uid']:
                await ctx.send("This subscription already exists!")
                return
        subs.append(newSub)
        await self.conf.guild(ctx.guild).subscriptions.set(subs)
        await ctx.send(f"Subscription added: {newSub}")
    
    @checks.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    @tube.command()
    async def unsubscribe(self, ctx: commands.Context, channelYouTube, channelDiscord: discord.TextChannel = None):
        """Unsubscribe a Discord channel from a YouTube channel
        
        If no Discord channel is specified, the subscription will be removed from all channels"""
        subs = await self.conf.guild(ctx.guild).subscriptions()
        unsubbed = []
        if channelDiscord:
            newSub = {'id': channelYouTube,
                      'channel': {"name": channelDiscord.name,
                                  "id": channelDiscord.id}}
            newSub['uid'] = self.sub_uid(newSub)
            for i, sub in enumerate(subs):
                if sub['uid'] == newSub['uid']:
                    unsubbed.append(subs.pop(i))
                    break
            else:
                await ctx.send("Subscription not found")
                return
        else:
            for i, sub in enumerate(subs):
                if sub['id'] == channelYouTube:
                    unsubbed.append(subs.pop(i))
            if not len(unsubbed):
                await ctx.send("Subscription not found")
                return
        await self.conf.guild(ctx.guild).subscriptions.set(subs)
        await ctx.send(f"Subscription(s) removed: {unsubbed}")
    
    @commands.guild_only()
    @tube.command(name="list")
    async def showsubs(self, ctx: commands.Context):
        """List current subscriptions"""
        subs = await self.conf.guild(ctx.guild).subscriptions()
        if not len(subs):
            await ctx.send("No subscriptions yet - try adding some!")
            return
        embed = discord.Embed()
        embed.title = "Tube Subs"
        subs_by_channel = {}
        for sub in subs:
            channel = f'{sub["channel"]["name"]} ({sub["channel"]["id"]})'
            subs_by_channel[channel] = subs_by_channel.get(channel, []).append(sub["id"])
        for channel, sub_ids in subs_by_channel.items():
            embed.add_field(name=channel,
                            value=sub_ids,
                            inline=False)
        await ctx.send(embed=embed)
    
    def sub_uid(self, subscription: dict):
        """A subscription must have a unique combination of YouTube channel ID and Discord channel"""
        try:
            canonicalString = f'{subscription["id"]}:{subscription["channel"]["id"]}'
        except KeyError:
            raise ValueError("Subscription object is malformed")
        return hashlib.sha256(canonicalString.encode()).hexdigest()
    
    @checks.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    @tube.command(name="update")
    async def get_new_videos(self, ctx: commands.Context = None):
        """Update feeds and post new videos"""
        fetchedSubs = {}
        for guild in self.bot.guilds:
            try:
                subs = await self.conf.guild(guild).subscriptions()
            except:
                continue
            altered = False
            for i, sub in enumerate(subs):
                channel = self.bot.get_channel(int(sub["channel"]["id"]))
                if not channel:
                    continue
                if not sub["id"] in fetchedSubs.keys():
                    try:
                        fetchedSubs[sub["id"]] = feedparser.parse(await self.get_feed(sub["id"]))
                    except Exception as e:
                        log.exception(f"Error parsing feed for {sub['id']}")
                        continue
                last_video_time = datetime.datetime.fromtimestamp(
                    time.mktime(
                        time.strptime(
                            sub.get("previous", "1970-01-01T00:00:00+00:00"),
                            "%Y-%m-%dT%H:%M:%S%z"
                        )
                    )
                )
                previous = sub.get("previous", False)
                for entry in fetchedSubs[sub["id"]]["entries"][::-1]:
                    published = datetime.datetime.fromtimestamp(time.mktime(entry["published_parsed"]))
                    if published > last_video_time + datetime.timedelta(seconds=1):
                        altered = True
                        subs[i]["previous"] = entry["published"]
                        # Prevent posting all the videos on the first run
                        if previous:
                            await self.bot.send_filtered(channel, content=entry["link"])
            if altered:
                await self.conf.guild(guild).subscriptions.set(subs)

    async def get_feed(self, channel):
        """Fetch data from a feed"""
        timeout = aiohttp.client.ClientTimeout(total=5)
        try:
            async with self.session.get(f"https://www.youtube.com/feeds/videos.xml?channel_id={channel}") as session:
                res = await session.read()
        except Exception as e:
            log.exception(f"Failed to get feed for channel {channel}: ", exc_info=e)
            return None
        return res

    def cog_unload(self):
        if self.bg_loop_task:
            self.bg_loop_task.cancel()
        asyncio.create_task(self.session.close())

    async def bg_loop(self):
        await self.bot.wait_until_ready()
        while await asyncio.sleep(300, True):
            await self.get_new_videos()
