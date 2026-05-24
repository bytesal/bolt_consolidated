import discord
from discord.ext import commands

class ReceptionCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="setwelcome")
    async def set_welcome_config(self, ctx, target_channel_id: int, *, welcome_message: str):
        db_cog = self.bot.get_cog("DatabaseCog")
        if not ctx.author.guild_permissions.administrator and ctx.author.id not in self.bot.DEVELOPER_IDS:
            return await ctx.send("❌ Missing Admin Privileges.")
            
        link = await db_cog.get_server_link(ctx.guild.id)
        if not link:
            return await ctx.send("❌ System Routing Error: Run this command from within the designated Staff Server.")

        await db_cog.reception.update_one(
            {"guild_id": str(link["public_guild_id"])},
            {"$set": {"welcome_channel": str(target_channel_id), "welcome_text": welcome_message}},
            upsert=True
        )
        await ctx.send(f"✅ Configured: Public greetings map safely to channel `{target_channel_id}`.")

    @commands.command(name="setleave")
    async def set_leave_config(self, ctx, target_channel_id: int, *, leave_message: str):
        db_cog = self.bot.get_cog("DatabaseCog")
        if not ctx.author.guild_permissions.administrator and ctx.author.id not in self.bot.DEVELOPER_IDS:
            return await ctx.send("❌ Missing Admin Privileges.")

        link = await db_cog.get_server_link(ctx.guild.id)
        if not link:
            return await ctx.send("❌ System Routing Error: Run this command from within the designated Staff Server.")

        await db_cog.reception.update_one(
            {"guild_id": str(link["public_guild_id"])},
            {"$set": {"leave_channel": str(target_channel_id), "leave_text": leave_message}},
            upsert=True
        )
        await ctx.send(f"✅ Configured: Public departures map safely to channel `{target_channel_id}`.")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        db_cog = self.bot.get_cog("DatabaseCog")
        cfg = await db_cog.reception.find_one({"guild_id": str(member.guild.id)})
        if cfg and cfg.get("welcome_channel"):
            channel = self.bot.get_channel(int(cfg["welcome_channel"]))
            if channel:
                text = cfg["welcome_text"].replace("{user}", member.mention).replace("{server}", member.guild.name)
                await channel.send(text)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        db_cog = self.bot.get_cog("DatabaseCog")
        cfg = await db_cog.reception.find_one({"guild_id": str(member.guild.id)})
        if cfg and cfg.get("leave_channel"):
            channel = self.bot.get_channel(int(cfg["leave_channel"]))
            if channel:
                text = cfg["leave_text"].replace("{user}", member.name).replace("{server}", member.guild.name)
                await channel.send(text)

async def setup(bot):
    await bot.add_cog(ReceptionCog(bot))
