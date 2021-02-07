import discord
import inspirobot
from redbot.core import commands

class Inspire(commands.Cog):
    """ Provides inspiration from the InspiroBot API """
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def inspire(self, ctx: commands.Context):
        """ Become someone who is inspired """
        if not ctx.channel.permissions_for(ctx.guild.me).embed_links:
            await ctx.send("They won't let me do that here.")
            return
        inspiration = inspirobot.generate()
        embed = discord.Embed(url=inspiration.url, title = f"Inspiration for {ctx.author.display_name}", color=await ctx.embed_color())
        embed.set_image(url=inspiration.url)
        await ctx.send(embed=embed)
