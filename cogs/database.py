import os
import discord
from discord.ext import commands
from motor.motor_asyncio import AsyncIOMotorClient

class DatabaseCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Support both naming conventions found in Render and local environments
        mongo_uri = os.getenv("MONGO_URI") or os.getenv("MONGODB_URI")
        if not mongo_uri:
            raise ValueError("CRITICAL: MONGO_URI or MONGODB_URI environment variable is missing.")
        
        self.client = AsyncIOMotorClient(mongo_uri)
        self.db = self.client["bolt_multi_server_db"]

        # Infrastructure Collections
        self.settings = self.db["global_settings"]
        self.server_links = self.db["server_links"]
        self.leveling = self.db["user_levels"]
        self.reception = self.db["reception_config"]
        self.jobs = self.db["hr_jobs"]
        self.applications = self.db["hr_applications"]
        self.hr_logs = self.db["hr_action_logs"]
        self.staff_ranks = self.db["staff_ranks_dropdown"]
        self.modmail_tickets = self.db["modmail_tickets"]
        self.modmail_stats = self.db["modmail_performance_stats"]
        self.mod_cases = self.db["moderation_cases"]
        self.mod_users = self.db["moderation_user_profiles"]
        self.sticky_messages = self.db["sticky_messages"]
        self.staff_quota_profiles = self.db["staff_quota_profiles"]
        self.staff_global_config = self.db["staff_global_config"]

    async def get_guild_prefix(self, guild_id: int):
        try:
            doc = await self.settings.find_one({"_id": f"prefix_{guild_id}"})
            return doc["value"] if doc else None
        except Exception as e:
            print(f"[Database Error] Failed to fetch prefix for guild {guild_id}: {e}")
            return None

    async def set_guild_prefix(self, guild_id: int, prefix: str):
        try:
            await self.settings.update_one({"_id": f"prefix_{guild_id}"}, {"$set": {"value": prefix}}, upsert=True)
        except Exception as e:
            print(f"[Database Error] Failed to set prefix for guild {guild_id}: {e}")

    async def get_server_link(self, staff_guild_id: int):
        try:
            return await self.server_links.find_one({"staff_guild_id": staff_guild_id})
        except Exception as e:
            print(f"[Database Error] Failed to fetch server link for staff guild {staff_guild_id}: {e}")
            return None

    async def get_link_by_public(self, public_guild_id: int):
        try:
            return await self.server_links.find_one({"public_guild_id": public_guild_id})
        except Exception as e:
            print(f"[Database Error] Failed to fetch link for public guild {public_guild_id}: {e}")
            return None

    async def link_servers(self, staff_guild_id: int, public_guild_id: int):
        try:
            await self.server_links.update_one(
                {"staff_guild_id": staff_guild_id},
                {"$set": {"public_guild_id": public_guild_id}},
                upsert=True
            )
        except Exception as e:
            print(f"[Database Error] Failed to link staff {staff_guild_id} with public {public_guild_id}: {e}")

    async def restore_persistent_views(self):
        # Hooks custom button/modal views onto the main execution stack across cycles
        print("[Database Engine] Restoring active dynamic view interactions...")

async def setup(bot):
    await bot.add_cog(DatabaseCog(bot))
