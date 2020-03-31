# -*- coding: utf-8 -*-
import asyncio
import json
import logging
import re
from collections import namedtuple
from typing import Optional, Union
from urllib.parse import parse_qsl, unquote, urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen

import discord
from redbot.core import Config, bot, checks, commands

log = logging.getLogger("red.cogs.scrub")

__all__ = ["UNIQUE_ID", "Scrub"]

UNIQUE_ID = 0x7363727562626572


class Scrub(commands.Cog):
    """URL parsing and processing functions based on code from Uroute: https://github.com/walterl/uroute"""
    def __init__(self, bot: bot.Red, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.conf = Config.get_conf(self, identifier=UNIQUE_ID, force_registration=True)
        self.conf.register_global(rules={})

    def clean_url(self, url):
        """Clean the given URL with the loaded rules data.
        The format of `rules` is the parsed JSON found in ClearURLs's
        [`data.min.json`](https://gitlab.com/KevinRoebert/ClearUrls/blob/master/data/data.min.json)
        file.
        URLs matching a provider's `urlPattern` and one of that provider's
        redirection patterns, will cause the URL to be replaced with the
        match's first matched group.
        """
        for provider in self.rules['providers'].values():
            if not re.match(provider['urlPattern'], url, re.IGNORECASE):
                continue
            if any(
                re.match(exc, url, re.IGNORECASE)
                for exc in provider['exceptions']
            ):
                continue
            for redir in provider['redirections']:
                match = re.match(redir, url, re.IGNORECASE)
                try:
                    if match and match.group(1):
                        return unquote(match.group(1))
                except IndexError:
                    # If we get here, we got a redirection match, but no
                    # matched grouped. The redirection rule is probably
                    # faulty.
                    pass
            parsed_url = urlparse(url)
            query_params = parse_qsl(parsed_url.query)

            for rule in provider['rules']:
                query_params = [
                    param for param in query_params
                    if not re.match(rule, param[0])
                ]
            url = urlunparse((
                parsed_url.scheme,
                parsed_url.netloc,
                parsed_url.path,
                parsed_url.params,
                urlencode(query_params),
                parsed_url.fragment,
            ))
        return url

    @commands.Cog.listener()
    async def on_message(self, message):
        rules = await self.conf.rules()
        if rules == {}:
            log.debug('Downloading rules data')
            request = Request(
                'https://gitlab.com/KevinRoebert/ClearUrls/raw/master/data/data.min.json',
                headers={'User-Agent': 'Red Scrubber (python urllib)'}
            )
            rules = json.loads(urlopen(request).read().decode())
            await self.conf.rules.set(rules)
        self.rules = rules
        links = list(set(re.findall(r'https?://(\S+)', message.content)))
        cleaned_links = []
        for link in links:
            cleaned_link = self.clean_url(link)
            if link != cleaned_link:
                cleaned_links.append(cleaned_link)
        if not len(cleaned_links):
            return
        plural = 'is' if len(cleaned_links) == 1 else 'ese'
        response = f"I scrubbed th{plural} for you:\n" + "\n".join(cleaned_links)
        await self.bot.send_filtered(message.channel, content=response)
