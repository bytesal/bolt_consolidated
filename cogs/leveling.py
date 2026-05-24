import discord
from discord import app_commands
from discord.ext import commands


class LevelingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ------------------------------------------------------------------
    # XP listener — fires on every message in a linked public server
    # ------------------------------------------------------------------

    @commands.Cog.listener()
    async def on_message(self, message):
        # Ignore bots and DMs
        if message.author.bot or not message.guild:
            return

        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return

        # Only track XP in servers that are linked as public servers
        link = await db_cog.get_link_by_public(message.guild.id)
        if not link:
            return

        user_id  = str(message.author.id)
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
                await message.channel.send(
                    f"🎉 Congratulations {message.author.mention}! "
                    f"You leveled up to **Level {doc['level']}**!"
                )
            except Exception:
                pass  # Channel send failure is non-critical

        await db_cog.leveling.update_one(
            {"user_id": user_id, "guild_id": guild_id},
            {"$set": {"xp": doc["xp"], "level": doc["level"]}},
            upsert=True,
        )

    # ------------------------------------------------------------------
    # /rank — display a member's level and XP
    # ------------------------------------------------------------------

    @app_commands.command(
        name="rank",
        description="Check your current level and XP progress.",
    )
    @app_commands.describe(member="The member to check. Defaults to yourself.")
    async def rank_command(
        self, interaction: discord.Interaction, member: discord.Member = None
    ):
        target = member or interaction.user

        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.response.send_message(
                "❌ Database connection unavailable.", ephemeral=True
            )

        doc = await db_cog.leveling.find_one(
            {"user_id": str(target.id), "guild_id": str(interaction.guild.id)}
        )
        if not doc:
            doc = {"xp": 0, "level": 1}

        level        = doc.get("level", 1)
        xp           = doc.get("xp", 0)
        next_level_xp = level * 200

        embed = discord.Embed(
            title=f"Rank — {target.display_name}",
            color=discord.Color.magenta(),
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="Level", value=str(level), inline=True)
        embed.add_field(
            name="XP", value=f"{xp} / {next_level_xp}", inline=True
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(LevelingCog(bot))
