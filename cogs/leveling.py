import discord
from discord.ext import commands

class LevelingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return
            
        # Confirm if the server is linked as a public frame
        link = await db_cog.get_link_by_public(message.guild.id)
        if not link:
            return

        user_id = str(message.author.id)
        guild_id = str(message.guild.id)

        doc = await db_cog.leveling.find_one({"user_id": user_id, "guild_id": guild_id})
        if not doc:
            doc = {"user_id": user_id, "guild_id": guild_id, "xp": 0, "level": 1}

        doc["xp"] += 15
        next_level_xp = doc["level"] * 200

        if doc["xp"] >= next_level_xp:
            doc["level"] += 1
            doc["xp"] -= next_level_xp
            try:
                await message.channel.send(f"🎉 Fantastic, {message.author.mention}! You scaled into structural tier **Level {doc['level']}**!")
            except Exception:
                pass

        await db_cog.leveling.update_one(
            {"user_id": user_id, "guild_id": guild_id},
            {"$set": {"xp": doc["xp"], "level": doc["level"]}},
            upsert=True
        )

    @commands.command(name="rank")
    async def rank_command(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        db_cog = self.bot.get_cog("DatabaseCog")
        guild_id = str(ctx.guild.id)
        user_id = str(member.id)

        doc = await db_cog.leveling.find_one({"user_id": user_id, "guild_id": guild_id})
        if not doc:
            doc = {"xp": 0, "level": 1}

        embed = discord.Embed(title=f"Progression Record — {member.name}", color=discord.Color.magenta())
        embed.add_field(name="Current Rank Value", value=f"Level {doc.get('level', 1)}", inline=True)
        embed.add_field(name="Accumulated XP Pool", value=f"{doc.get('xp', 0)} / {doc.get('level', 1) * 200} XP", inline=True)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(LevelingCog(bot))
