import discord
from discord.ext import commands
from datetime import datetime, timedelta
import asyncio
import re
import time

INVITE_REGEX = r"(discord\.gg\/|discord\.com\/invite\/)"
URL_REGEX = r"(https?:\/\/[^\s]+)"


class AutoModCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.spam_cache = {}
        self.slowmode_tasks = {}  # guild_id: asyncio.Task

    async def get_settings(self, guild_id):
        db_cog = self.bot.get_cog("DatabaseCog")
        settings = await db_cog.automod.find_one({"_id": str(guild_id)})
        if not settings:
            settings = {
                "_id": str(guild_id),
                "anti_links": False,
                "anti_invites": True,
                "anti_spam": False,
                "anti_mentions": False,
                "allowed_ad_channels": [],
                "mention_limit": 5,
                "spam_messages": 5,
                "spam_seconds": 6,
                "punishment": "timeout",
                "timeout_duration": 10,
                "anti_spam_slowmode": False,      # new
                "slowmode_duration": 5,            # seconds
                "slowmode_trigger": 20,            # messages in 5 seconds
            }
            await db_cog.automod.insert_one(settings)
        return settings

    async def punish(self, member, reason, settings):
        punishment = settings.get("punishment", "timeout")
        if punishment == "timeout":
            duration = settings.get("timeout_duration", 10)
            until = datetime.utcnow() + timedelta(minutes=duration)
            try:
                await member.timeout(until, reason=reason)
            except Exception:
                pass
        elif punishment == "kick":
            try:
                await member.kick(reason=reason)
            except Exception:
                pass
        elif punishment == "ban":
            try:
                await member.ban(reason=reason)
            except Exception:
                pass

    async def enable_slowmode(self, channel, duration_seconds, guild_id):
        """Enable slowmode and schedule removal if needed."""
        try:
            await channel.edit(slowmode_delay=duration_seconds)
            # Cancel any existing task for this guild
            if guild_id in self.slowmode_tasks:
                self.slowmode_tasks[guild_id].cancel()
            # Schedule removal after 60 seconds
            async def reset_slowmode():
                await asyncio.sleep(60)
                try:
                    await channel.edit(slowmode_delay=0)
                except Exception:
                    pass
                finally:
                    self.slowmode_tasks.pop(guild_id, None)
            task = asyncio.create_task(reset_slowmode())
            self.slowmode_tasks[guild_id] = task
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.guild:
            return
        if message.author.bot:
            return
        if message.author.id in self.bot.DEVELOPER_IDS:
            return
        if message.author.guild_permissions.administrator:
            return

        settings = await self.get_settings(message.guild.id)

        # Anti-links
        if settings.get("anti_links"):
            if re.search(URL_REGEX, message.content):
                try:
                    await message.delete()
                except Exception:
                    pass
                warning = await message.channel.send(f"{message.author.mention} ❌ Links are not allowed.")
                await asyncio.sleep(5)
                try:
                    await warning.delete()
                except Exception:
                    pass
                await self.punish(message.author, "AutoMod: Links detected.", settings)
                return

        # Anti-invites
        if settings.get("anti_invites"):
            allowed = settings.get("allowed_ad_channels", [])
            if re.search(INVITE_REGEX, message.content):
                if message.channel.id not in allowed:
                    try:
                        await message.delete()
                    except Exception:
                        pass
                    warning = await message.channel.send(f"{message.author.mention} ❌ Advertising is only allowed in designated channels.")
                    await asyncio.sleep(5)
                    try:
                        await warning.delete()
                    except Exception:
                        pass
                    return

        # Anti-mention spam
        if settings.get("anti_mentions"):
            mention_limit = settings.get("mention_limit", 5)
            if len(message.mentions) >= mention_limit:
                try:
                    await message.delete()
                except Exception:
                    pass
                warning = await message.channel.send(f"{message.author.mention} ❌ Mention spam detected.")
                await asyncio.sleep(5)
                try:
                    await warning.delete()
                except Exception:
                    pass
                await self.punish(message.author, "AutoMod: Mention spam detected.", settings)
                return

        # Anti-spam + slowmode
        if settings.get("anti_spam") or settings.get("anti_spam_slowmode"):
            user_id = message.author.id
            now = time.time()
            if user_id not in self.spam_cache:
                self.spam_cache[user_id] = []
            self.spam_cache[user_id].append(now)
            spam_seconds = settings.get("spam_seconds", 6)
            self.spam_cache[user_id] = [t for t in self.spam_cache[user_id] if now - t <= spam_seconds]
            spam_messages = settings.get("spam_messages", 5)
            if len(self.spam_cache[user_id]) >= spam_messages:
                # Spam detected
                try:
                    await message.channel.purge(limit=10, check=lambda m: m.author.id == user_id)
                except Exception:
                    pass
                warning = await message.channel.send(f"{message.author.mention} ❌ Spam detected.")
                await asyncio.sleep(5)
                try:
                    await warning.delete()
                except Exception:
                    pass
                if settings.get("anti_spam"):
                    await self.punish(message.author, "AutoMod: Spam detected.", settings)
                # Slowmode activation
                if settings.get("anti_spam_slowmode"):
                    duration = settings.get("slowmode_duration", 5)
                    await self.enable_slowmode(message.channel, duration, message.guild.id)

    # ---------- Commands ----------
    @commands.hybrid_group(name="automod", invoke_without_command=True)
    async def automod(self, ctx):
        await ctx.send("**Available AutoMod Commands**\n\n`!automod links true/false`\n`!automod spam true/false`\n`!automod mentions true/false`\n`!automod slowmode true/false`\n`!allowads`\n`!removeads`")

    @automod.command(name="links")
    async def automod_links(self, ctx, enabled: bool):
        if not ctx.author.guild_permissions.administrator:
            return await ctx.send("❌ Administrator required.")
        db_cog = self.bot.get_cog("DatabaseCog")
        await db_cog.automod.update_one({"_id": str(ctx.guild.id)}, {"$set": {"anti_links": enabled}}, upsert=True)
        await ctx.send(f"✅ Anti-links set to `{enabled}`")

    @automod.command(name="spam")
    async def automod_spam(self, ctx, enabled: bool):
        if not ctx.author.guild_permissions.administrator:
            return await ctx.send("❌ Administrator required.")
        db_cog = self.bot.get_cog("DatabaseCog")
        await db_cog.automod.update_one({"_id": str(ctx.guild.id)}, {"$set": {"anti_spam": enabled}}, upsert=True)
        await ctx.send(f"✅ Anti-spam set to `{enabled}`")

    @automod.command(name="mentions")
    async def automod_mentions(self, ctx, enabled: bool):
        if not ctx.author.guild_permissions.administrator:
            return await ctx.send("❌ Administrator required.")
        db_cog = self.bot.get_cog("DatabaseCog")
        await db_cog.automod.update_one({"_id": str(ctx.guild.id)}, {"$set": {"anti_mentions": enabled}}, upsert=True)
        await ctx.send(f"✅ Anti-mentions set to `{enabled}`")

    @automod.command(name="slowmode")
    async def automod_slowmode(self, ctx, enabled: bool):
        if not ctx.author.guild_permissions.administrator:
            return await ctx.send("❌ Administrator required.")
        db_cog = self.bot.get_cog("DatabaseCog")
        await db_cog.automod.update_one({"_id": str(ctx.guild.id)}, {"$set": {"anti_spam_slowmode": enabled}}, upsert=True)
        await ctx.send(f"✅ Auto‑slowmode set to `{enabled}`")

    @automod.command(name="allowads")
    async def allow_ads(self, ctx):
        if not ctx.author.guild_permissions.administrator:
            return await ctx.send("❌ Administrator required.")
        db_cog = self.bot.get_cog("DatabaseCog")
        await db_cog.automod.update_one(
            {"_id": str(ctx.guild.id)},
            {"$addToSet": {"allowed_ad_channels": ctx.channel.id}, "$set": {"anti_invites": True}},
            upsert=True
        )
        try:
            await ctx.message.delete()
        except Exception:
            pass
        confirmation = await ctx.send("✅ Ads are now allowed in this channel.")
        await asyncio.sleep(5)
        try:
            await confirmation.delete()
        except Exception:
            pass

    @automod.command(name="removeads")
    async def remove_ads(self, ctx):
        if not ctx.author.guild_permissions.administrator:
            return await ctx.send("❌ Administrator required.")
        db_cog = self.bot.get_cog("DatabaseCog")
        await db_cog.automod.update_one(
            {"_id": str(ctx.guild.id)},
            {"$pull": {"allowed_ad_channels": ctx.channel.id}}
        )
        try:
            await ctx.message.delete()
        except Exception:
            pass
        confirmation = await ctx.send("✅ Ads disabled in this channel.")
        await asyncio.sleep(5)
        try:
            await confirmation.delete()
        except Exception:
            pass


async def setup(bot):
    await bot.add_cog(AutoModCog(bot))
