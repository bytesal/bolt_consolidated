import os
import discord
from discord.ext import commands
from motor.motor_asyncio import AsyncIOMotorClient

from cogs.applications import ReviewButtons
from cogs.staff_quota import StaffQuotaView, RanksDropdownView
from cogs.modmail import TicketControls


class DatabaseCog(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

        mongo_uri = (
            os.getenv("MONGO_URI")
            or os.getenv("MONGODB_URI")
        )

        if not mongo_uri:
            raise ValueError("CRITICAL: MONGO_URI or MONGODB_URI is missing.")

        self.client = AsyncIOMotorClient(mongo_uri)
        self.db = self.client["bolt_multi_server_db"]

        # Collections
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
        self.blacklist = self.db["global_blacklist"]
        self.staff_teams = self.db["staff_teams"]
        self.ad_warns = self.db["ad_warns"]  # New collection for ad-warns

    # ------------------------------------------------------------
    # Prefix Helpers
    # ------------------------------------------------------------
    async def get_guild_prefix(self, guild_id: int):
        try:
            doc = await self.settings.find_one({"_id": f"prefix_{guild_id}"})
            return doc["value"] if doc else None
        except Exception as e:
            print(f"[Database Error] Failed to fetch prefix for guild {guild_id}: {e}")
            return None

    async def set_guild_prefix(self, guild_id: int, prefix: str):
        try:
            await self.settings.update_one(
                {"_id": f"prefix_{guild_id}"},
                {"$set": {"value": prefix}},
                upsert=True
            )
        except Exception as e:
            print(f"[Database Error] Failed to set prefix for guild {guild_id}: {e}")

    # ------------------------------------------------------------
    # Server Link Helpers
    # ------------------------------------------------------------
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

    async def unlink_servers(self, staff_guild_id: int):
        try:
            await self.server_links.delete_one({"staff_guild_id": staff_guild_id})
        except Exception as e:
            print(f"[Database Error] Failed to unlink staff guild {staff_guild_id}: {e}")

    async def update_server_link(self, old_staff_guild_id: int, new_staff_guild_id: int = None, new_public_guild_id: int = None):
        update_data = {}
        if new_staff_guild_id:
            update_data["staff_guild_id"] = new_staff_guild_id
        if new_public_guild_id:
            update_data["public_guild_id"] = new_public_guild_id
        try:
            await self.server_links.update_one(
                {"staff_guild_id": old_staff_guild_id},
                {"$set": update_data}
            )
        except Exception as e:
            print(f"[Database Error] Failed to update server link: {e}")

    # ------------------------------------------------------------
    # Persistent View Restoration
    # ------------------------------------------------------------
    async def restore_persistent_views(self):
        print("[Database Engine] Restoring persistent views...")

        # HR Application Review Buttons
        try:
            async for app_doc in self.applications.find({"status": "pending"}):
                app_id = str(app_doc["_id"])
                job_name = app_doc.get("job_name", "Unknown Position")
                self.bot.add_view(ReviewButtons(self.bot, app_id, job_name))
        except Exception as e:
            print(f"[View Restore] Failed to restore ReviewButtons: {e}")

        # Staff Quota Dashboard
        try:
            self.bot.add_view(StaffQuotaView(self.bot))
        except Exception as e:
            print(f"[View Restore] Failed to restore StaffQuotaView: {e}")

        # Rank Dropdown
        try:
            ranks_map = {}
            async for r in self.staff_ranks.find():
                ranks_map[r["name"]] = r.get("description", "")
            if not ranks_map:
                ranks_map["Default"] = "Pending configuration."
            self.bot.add_view(RanksDropdownView(ranks_map))
        except Exception as e:
            print(f"[View Restore] Failed to restore RanksDropdownView: {e}")

        # Open Modmail Tickets
        try:
            async for ticket in self.modmail_tickets.find({"status": "open"}):
                if ticket.get("user_id"):
                    self.bot.add_view(TicketControls(self.bot))
        except Exception as e:
            print(f"[View Restore] Failed to restore TicketControls: {e}")

        print("[Database Engine] Persistent view restoration complete.")


async def setup(bot):
    await bot.add_cog(DatabaseCog(bot))
