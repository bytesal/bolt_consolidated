import discord
from discord.ext import commands
from discord import app_commands

class CoreCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_dev(self, user_id: int) -> bool:
        return user_id in self.bot.DEVELOPER_IDS

    def clean_permission_check(self, ctx, perm: str = None) -> bool:
        if self.is_dev(ctx.author.id):
            return True
        if perm and hasattr(ctx.author.guild_permissions, perm):
            return getattr(ctx.author.guild_permissions, perm)
        return ctx.author.guild_permissions.administrator

    @commands.command(name="linkserver")
    async def link_server_command(self, ctx, public_guild_id: int):
        if not self.clean_permission_check(ctx):
            return await ctx.send("❌ Access Denied: Administrator permission or Developer identity verification failed.")
        db_cog = self.bot.get_cog("DatabaseCog")
        await db_cog.link_servers(ctx.guild.id, public_guild_id)
        
        embed = discord.Embed(
            title="Server Inter-Link Implemented",
            description=f"This channel cluster has been defined as the **Staff Server**.\nLinked Public Server Target: `{public_guild_id}`",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @commands.command(name="setprefix")
    async def set_prefix_command(self, ctx, prefix: str):
        if not self.clean_permission_check(ctx):
            return await ctx.send("❌ Access Denied: Missing administrative permissions.")
        db_cog = self.bot.get_cog("DatabaseCog")
        await db_cog.set_guild_prefix(ctx.guild.id, prefix)
        await ctx.send(f"✅ Executed: Prefix updated to `{prefix}` for this guild.")

    @commands.command(name="botstatus")
    async def bot_status_command(self, ctx, status_type: str, *, activity_text: str):
        if not self.is_dev(ctx.author.id):
            return await ctx.send("❌ Core Security Error: Command limited to Global System Developers.")
        
        status_map = {
            "online": discord.Status.online,
            "idle": discord.Status.idle,
            "dnd": discord.Status.dnd,
            "invisible": discord.Status.invisible
        }
        status = status_map.get(status_type.lower(), discord.Status.online)
        activity = discord.Game(name=activity_text)
        await self.bot.change_presence(status=status, activity=activity)
        await ctx.send("✅ System Presence modifications pushed to API successfully.")

    @commands.command(name="setbotname")
    async def set_bot_name_command(self, ctx, *, new_name: str):
        if not self.is_dev(ctx.author.id):
            return await ctx.send("❌ Core Security Error: Command limited to Global System Developers.")
        try:
            await self.bot.user.edit(username=new_name)
            await ctx.send(f"✅ System application identity renamed to: **{new_name}**")
        except Exception as e:
            await ctx.send(f"❌ API Identity Assignment Refused: {e}")

    @commands.command(name="sync")
    async def sync_slash_commands(self, ctx, scope: str = "guild"):
        if not self.clean_permission_check(ctx):
            return await ctx.send("❌ Access Denied.")
        if scope == "global":
            synced = await self.bot.tree.sync()
            await ctx.send(f"✅ Globally synced `{len(synced)}` application slash commands to Discord registry.")
        else:
            self.bot.tree.copy_global_to(guild=ctx.guild)
            synced = await self.bot.tree.sync(guild=ctx.guild)
            await ctx.send(f"✅ Local sync operations resolved. `{len(synced)}` context commands configured inside this guild.")

    @commands.command(name="help")
    async def comprehensive_help(self, ctx):
        db_cog = self.bot.get_cog("DatabaseCog")
        is_staff = await db_cog.get_server_link(ctx.guild.id)
        is_public = await db_cog.get_link_by_public(ctx.guild.id)

        embed = discord.Embed(
            title="⚡ Comprehensive System Operations Core",
            description="Dynamically adapting visual indexing to your local execution scope.",
            color=discord.Color.blue()
        )

        if is_staff or self.is_dev(ctx.author.id):
            embed.add_field(
                name="🛡️ Staff Server Executive Commands",
                value=(
                    "`!linkserver <Public ID>` - Interconnect server frames\n"
                    "`!setprefix <Symbol>` - Alter dynamic routing parameters\n"
                    "`!setwelcome <Channel ID> <Message>` - Stage public greetings\n"
                    "`!setleave <Channel ID> <Message>` - Stage departure alerts\n"
                    "`!sethrchannel` - Declare active application routing context\n"
                    "`!hrlogs [Staff]` - Interrogate system log databases\n"
                    "`!addrank <Name> <Emoji> <Description>` - Generate duty interfaces\n"
                    "`!addduty <Rank> <Responsibility>` - Bind specific requirements\n"
                    "`!removedepartment <Staff ID>` - Purge individual from specialized department allocations\n"
                    "`!shift` / `!quota` - Access workload matrices manually"
                ),
                inline=False
            )

        if is_public or not is_staff:
            embed.add_field(
                name="🌍 Main Public Server Commands",
                value=(
                    "`!rank` - Evaluate localized structural leveling values\n"
                    "`!apply` - Trigger standard application request process\n"
                    "`/warn` / `/adwarn` - Trigger tracking systems (For allocated mods inside tracking context)\n"
                    "`/sticky` - Fix visual elements directly to local terminal streams"
                ),
                inline=False
            )

        if self.is_dev(ctx.author.id):
            embed.add_field(
                name="🔧 Global Infrastructure Overrides (Dev Only)",
                value="`!botstatus <Type> <Text>` - Force presence states\n`!setbotname <Name>` - Change API application identity",
                inline=False
            )

        embed.set_footer(text="Bolt Multi-Server Platform Protocol v2.4 • Zero Shortcuts")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(CoreCog(bot))
