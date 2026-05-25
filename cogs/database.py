import os
import discord
from discord.ext import commands
from motor.motor_asyncio import AsyncIOMotorClient
import traceback
from utils.logger import get_logger

logger = get_logger("database")

# Import views – these must be importable even if database fails
try:
    from cogs.applications import ReviewButtons
    from cogs.staff_quota import StaffQuotaView, RanksDropdownView
    from cogs.modmail import TicketControls
except ImportError as e:
    logger.error(f"Failed to import view classes: {e}")
    # Define dummy placeholders to avoid NameError if import fails
    ReviewButtons = None
    StaffQuotaView = None
    RanksDropdownView = None
    TicketControls = None


class DatabaseCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.client = None
        self.db = None
        self._init_db()

    def _init_db(self):
        """Initialize MongoDB connection – safe, with error logging."""
        mongo_uri = os.getenv("MONGO_URI") or os.getenv("MONGODB_URI")
        if not mongo_uri:
            logger.critical("MONGO_URI or MONGODB_URI environment variable not set.")
            return

        try:
            self.client = AsyncIOMotorClient(mongo_uri)
            self.db = self.client["bolt_multi_server_db"]
            logger.info("MongoDB client created (connection will be established on first operation).")
        except Exception as e:
            logger.critical(f"Failed to create MongoDB client: {e}")
            self.client = None
            self.db = None
            return

        # Define collections (lazy – they will be created on first use)
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
        self.automod = self.db["automod"]
        self.ad_warns = self.db["ad_warns"]
        self.ticket_messages = self.db["ticket_messages"]
        self.audit_log = self.db["audit_log"]
        self.reaction_roles = self.db["reaction_roles"]
        self.role_backup = self.db["role_backup"]

    # ------------------------------------------------------------
    # Prefix Helpers
    # ------------------------------------------------------------
    async def get_guild_prefix(self, guild_id: int):
        if not self.db:
            return None
        try:
            doc = await self.settings.find_one({"_id": f"prefix_{guild_id}"})
            return doc["value"] if doc else None
        except Exception as e:
            logger.error(f"Failed to fetch prefix for guild {guild_id}: {e}")
            return None

    async def set_guild_prefix(self, guild_id: int, prefix: str):
        if not self.db:
            return
        try:
            await self.settings.update_one(
                {"_id": f"prefix_{guild_id}"},
                {"$set": {"value": prefix}},
                upsert=True
            )
        except Exception as e:
            logger.error(f"Failed to set prefix for guild {guild_id}: {e}")

    # ------------------------------------------------------------
    # Server Link Helpers
    # ------------------------------------------------------------
    async def get_server_link(self, staff_guild_id: int):
        if not self.db:
            return None
        try:
            return await self.server_links.find_one({"staff_guild_id": staff_guild_id})
        except Exception as e:
            logger.error(f"Failed to fetch server link for staff guild {staff_guild_id}: {e}")
            return None

    async def get_link_by_public(self, public_guild_id: int):
        if not self.db:
            return None
        try:
            return await self.server_links.find_one({"public_guild_id": public_guild_id})
        except Exception as e:
            logger.error(f"Failed to fetch link for public guild {public_guild_id}: {e}")
            return None

    async def link_servers(self, staff_guild_id: int, public_guild_id: int):
        if not self.db:
            return
        try:
            await self.server_links.update_one(
                {"staff_guild_id": staff_guild_id},
                {"$set": {"public_guild_id": public_guild_id}},
                upsert=True
            )
        except Exception as e:
            logger.error(f"Failed to link servers: {e}")

    async def unlink_servers(self, staff_guild_id: int):
        if not self.db:
            return
        try:
            await self.server_links.delete_one({"staff_guild_id": staff_guild_id})
        except Exception as e:
            logger.error(f"Failed to unlink servers: {e}")

    async def update_server_link(self, old_staff_guild_id: int, new_staff_guild_id: int = None, new_public_guild_id: int = None):
        if not self.db:
            return
        update_data = {}
        if new_staff_guild_id:
            update_data["staff_guild_id"] = new_staff_guild_id
        if new_public_guild_id:
            update_data["public_guild_id"] = new_public_guild_id
        if not update_data:
            return
        try:
            await self.server_links.update_one(
                {"staff_guild_id": old_staff_guild_id},
                {"$set": update_data}
            )
        except Exception as e:
            logger.error(f"Failed to update server link: {e}")

    # ------------------------------------------------------------
    # Index Management
    # ------------------------------------------------------------
    async def ensure_indexes(self):
        """Create necessary indexes for performance (if database connected)."""
        if not self.db:
            logger.warning("Database not connected – skipping index creation.")
            return
        try:
            await self.mod_cases.create_index("target_id")
            await self.mod_cases.create_index("case_id")
            await self.mod_cases.create_index("expires_at")
            await self.mod_users.create_index("_id")
            await self.ad_warns.create_index("target_id")
            await self.ad_warns.create_index("issuer_id")
            await self.staff_quota_profiles.create_index("department")
            await self.modmail_tickets.create_index("user_id")
            await self.modmail_tickets.create_index("status")
            await self.modmail_tickets.create_index("claimed_by")
            await self.ticket_messages.create_index("ticket_id")
            await self.audit_log.create_index("guild_id")
            await self.audit_log.create_index("timestamp")
            await self.reaction_roles.create_index("message_id")
            await self.reaction_roles.create_index("guild_id")
            await self.role_backup.create_index("user_id")
            await self.role_backup.create_index("guild_id")
            await self.role_backup.create_index("created_at", expireAfterSeconds=2592000)
            logger.info("All database indexes created/verified.")
        except Exception as e:
            logger.error(f"Index creation error: {e}")

    # ------------------------------------------------------------
    # Persistent View Restoration (only if database connected)
    # ------------------------------------------------------------
    async def restore_persistent_views(self):
        if not self.db:
            logger.warning("Database not connected – cannot restore persistent views.")
            return
        logger.info("Restoring persistent views...")
        try:
            if ReviewButtons is not None:
                async for app_doc in self.applications.find({"status": "pending"}):
                    app_id = str(app_doc["_id"])
                    job_name = app_doc.get("job_name", "Unknown Position")
                    self.bot.add_view(ReviewButtons(self.bot, app_id, job_name))
        except Exception as e:
            logger.error(f"Failed to restore ReviewButtons: {e}")
        try:
            if StaffQuotaView is not None:
                self.bot.add_view(StaffQuotaView(self.bot))
        except Exception as e:
            logger.error(f"Failed to restore StaffQuotaView: {e}")
        try:
            if RanksDropdownView is not None:
                ranks_map = {}
                async for r in self.staff_ranks.find():
                    ranks_map[r["name"]] = r.get("description", "")
                if not ranks_map:
                    ranks_map["Default"] = "Pending configuration."
                self.bot.add_view(RanksDropdownView(ranks_map))
        except Exception as e:
            logger.error(f"Failed to restore RanksDropdownView: {e}")
        try:
            if TicketControls is not None:
                async for ticket in self.modmail_tickets.find({"status": "open"}):
                    if ticket.get("user_id"):
                        self.bot.add_view(TicketControls(self.bot))
        except Exception as e:
            logger.error(f"Failed to restore TicketControls: {e}")
        logger.info("Persistent view restoration complete.")


async def setup(bot):
    await bot.add_cog(DatabaseCog(bot))
