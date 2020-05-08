# -*- coding: utf-8 -*-
import aiohttp
import asyncio
import json
import logging
import re
from collections import namedtuple
from typing import Optional, Union
from urllib.parse import parse_qsl, unquote, urlencode, urlparse, urlunparse

import discord
from redbot.core import Config, bot, checks, commands

log = logging.getLogger("red.cbd-cogs.scrub")

__all__ = ["UNIQUE_ID", "Scrub"]

UNIQUE_ID = 0x7363727562626572

URL_PATTERN = re.compile(r'(https?://\S+)')


class Scrub(commands.Cog):
    """Applies a set of rules to remove undesireable elements from hyperlinks
    
    URL parsing and processing functions based on code from Uroute (https://github.com/walterl/uroute)
    
    By default, this cog uses the URL cleaning rules provided by ClearURLs (https://gitlab.com/KevinRoebert/ClearUrls)"""
    def __init__(self, bot: bot.Red, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.conf = Config.get_conf(self, identifier=UNIQUE_ID, force_registration=True)
        self.conf.register_global(rules={}, url='https://kevinroebert.gitlab.io/ClearUrls/data/data.minify.json')

    def clean_url(self, url: str, rules: dict, loop: bool = True):
        """Clean the given URL with the provided rules data.

        The format of `rules` is defined by [ClearURLs](https://gitlab.com/KevinRoebert/ClearUrls/-/wikis/Technical-details/Rules-file).

        URLs matching a provider's `urlPattern` and one or more of that provider's redirection patterns will cause the URL to be replaced with the match's first matched group.
        """
        for provider_name, provider in rules.get('providers', {}).items():
            # Check provider urlPattern against provided URI
            if not re.match(provider['urlPattern'], url, re.IGNORECASE):
                continue

            # completeProvider is a boolean that determines if every url that
            # matches will be blocked. If you want to specify rules, exceptions
            # and/or redirections, the value of completeProvider must be false.
            if provider.get('completeProvider'):
                return False

            # If any exceptions are matched, this provider is skipped
            if any(re.match(exc, url, re.IGNORECASE)
                   for exc in provider.get('exceptions', [])):
                continue

            # If redirect found, recurse on target (only once)
            for redir in provider.get('redirections', []):
                match = re.match(redir, url, re.IGNORECASE)
                try:
                    if match and match.group(1):
                        if loop:
                            return self.clean_url(unquote(match.group(1)), rules, False)
                        else:
                            url = unquote(match.group(1))
                except IndexError:
                    log.warning(f"Redirect target match failed [{provider_name}]: {redir}")
                    pass

            # Explode query parameters to be checked against rules
            parsed_url = urlparse(url)
            query_params = parse_qsl(parsed_url.query)

            # Check regular rules and referral marketing rules
            for rule in (*provider.get('rules', []), *provider.get('referralMarketing', [])):
                query_params = [
                    param for param in query_params
                    if not re.match(rule, param[0], re.IGNORECASE)
                ]

            # Rebuild valid URI string with remaining query parameters
            url = urlunparse((
                parsed_url.scheme,
                parsed_url.netloc,
                parsed_url.path,
                parsed_url.params,
                urlencode(query_params),
                parsed_url.fragment,
            ))

            # Run raw rules against the full URI string
            for raw_rule in provider.get('rawRules', []):
                url = re.sub(raw_rule, '', url)
        return url

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        links = list(set(URL_PATTERN.findall(message.content)))
        if not links:
            return
        rules = await self.conf.rules()
        if rules == {}:
            rules = await self.update()
        cleaned_links = []
        for link in links:
            cleaned_link = self.clean_url(link, rules)
            if link not in (cleaned_link, unquote(cleaned_link)):
                cleaned_links.append(cleaned_link)
        if not len(cleaned_links):
            return
        plural = 'is' if len(cleaned_links) == 1 else 'ese'
        response = f"I scrubbed th{plural} for you:\n" + "\n".join([f"<{link}>" for link in cleaned_links])
        await self.bot.send_filtered(message.channel, content=response)

    @commands.command(name="scrubupdate")
    @checks.is_owner()
    async def scrub_update(self, ctx: commands.Context, url: str = None):
        """Update Scrub with the latest rules
        
        By default, Scrub will get rules from https://kevinroebert.gitlab.io/ClearUrls/data/data.minify.json
        
        This can be overridden by passing a `url` to this command with an alternative compatible rules file
        """
        confUrl = await self.conf.url()
        _url = url or confUrl
        try:
            await self.update(_url)
        except Exception as e:
            await ctx.send("Rules update failed (see log for details)")
            log.exception("Rules update failed", exc_info=e)
            return
        if _url != confUrl:
            await self.conf.url.set(url)
        await ctx.send("Rules updated")
    
    async def update(self, url):
        log.debug(f'Downloading rules data from {url}')
        session = aiohttp.ClientSession()
        async with session.get(url) as request:
            rules = json.loads(await request.read())
        await session.close()
        await self.conf.rules.set(rules)