# -*- coding: utf-8 -*-
from .tube import Tube

async def setup(bot):
    cog = Tube(bot)
    bot.add_cog(cog)
    cog.init()