from .inspire import Inspire

async def setup(bot):
    bot.add_cog(Inspire(bot))
