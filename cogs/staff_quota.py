import discord
from discord import app_commands
from discord.ext import commands, tasks
import datetime


# ---------------------------------------------------------------------------
# Department quota requirements
# ---------------------------------------------------------------------------

DEPARTMENT_QUOTAS = {
    "board":       {"weekly_messages": 20},
    "ceo":         {"weekly_messages": 20, "weekly_hires": 1},
    "chro":        {"weekly_messages": 20, "weekly_ads_staff": 40, "weekly_ads_server": 40, "weekly_checks": 1},
    "hr":          {"weekly_messages": 15, "weekly_ads_staff": 30, "weekly_ads_server": 30, "weekly_hires": 1},
    "mod":         {"weekly_messages": 15, "weekly_adwarns_executed": 5},
    "partnership": {"weekly_messages": 5,  "weekly_ads_staff": 20, "weekly_ads_server": 20, "weekly_partnerships": 5},
}


# ---------------------------------------------------------------------------
# Staff ranks dropdown
# ---------------------------------------------------------------------------

class StaffRanksDropdown(discord.ui.Select):
    def __init__(self, ranks_dict: dict):
        options = [
            discord.SelectOption(label=name, description=f"View duties for {name}")
            for name in list(ranks_dict.keys())[:25]
        ]
        if not options:
            options = [discord.SelectOption(label="No ranks configured yet.", value="empty")]

        super().__init__(
            placeholder="Select a staff rank to view its responsibilities...",
            options=options,
            custom_id="staff_ranks_dropdown_select_persistent",
        )

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "empty":
            return await interaction.response.send_message(
                "No ranks have been configured yet.", ephemeral=True
            )

        db_cog = interaction.client.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.response.send_message(
                "❌ Database connection unavailable.", ephemeral=True
            )

        rank = await db_cog.staff_ranks.find_one({"name": self.values[0]})
        if not rank:
            return await interaction.response.send_message(
                "❌ Rank not found in database.", ephemeral=True
            )

        embed = discord.Embed(
            title=f"Rank Details — {rank['name']}",
            description=rank.get("description", "No description provided."),
            color=discord.Color.purple(),
        )
        duties = rank.get("duties", [])
        if duties:
            embed.add_field(
                name="📋 Responsibilities",
                value="\n".join(f"• {d}" for d in duties),
                inline=False,
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class RanksDropdownView(discord.ui.View):
    def __init__(self, ranks_dict: dict):
        super().__init__(timeout=None)
        self.add_item(StaffRanksDropdown(ranks_dict))


# ---------------------------------------------------------------------------
# Quota / shift dashboard
# ---------------------------------------------------------------------------

class StaffQuotaView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot


# ---------------------------------------------------------------------------
# Cog
# ---------------------------------------------------------------------------

class StaffQuotaCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.weekly_evaluation_loop.start()

    def cog_unload(self):
        self.weekly_evaluation_loop.cancel()

    @tasks.loop(minutes=5.0)
    async def weekly_evaluation_loop(self):
        now = datetime.datetime.utcnow()
        if now.weekday() == 5 and now.hour == 23 and now.minute >= 55:
            db_cog = self.bot.get_cog("DatabaseCog")
            if not db_cog:
                return

            async for profile in db_cog.staff_quota_profiles.find():
                u_id = profile["_id"]

                await db_cog.staff_quota_profiles.update_one(
                    {"_id": u_id},
                    {
                        "$set": {
                            "weekly_messages": 0,
                            "weekly_ads_staff": 0,
                            "weekly_ads_server": 0,
                            "weekly_hires": 0,
                            "weekly_mod_actions": 0,
                            "weekly_partnerships": 0,
                            "weekly_checks": 0,
                            "weekly_adwarns_executed": 0,
                        }
                    },
                )

    @weekly_evaluation_loop.before_loop
    async def before_weekly_loop(self):
        await self.bot.wait_until_ready()

    # ------------------------------------------------------------------
    # /setdepartment
    # ------------------------------------------------------------------

    @app_commands.command(
        name="setdepartment",
        description="Assign a staff member to a department.",
    )
    @app_commands.describe(
        target_member="The staff member to assign.",
        department_key=f"Department name. Options: {', '.join(DEPARTMENT_QUOTAS.keys())}",
    )
    async def set_department_command(
        self,
        interaction: discord.Interaction,
        target_member: discord.Member,
        department_key: str,
    ):
        if (
            not interaction.user.guild_permissions.administrator
            and interaction.user.id not in self.bot.DEVELOPER_IDS
        ):
            return await interaction.response.send_message(
                "❌ Administrator permission required.", ephemeral=True
            )

        if department_key.lower() not in DEPARTMENT_QUOTAS:
            valid = ", ".join(f"`{k}`" for k in DEPARTMENT_QUOTAS)
            return await interaction.response.send_message(
                f"❌ Invalid department. Valid options: {valid}", ephemeral=True
            )

        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.response.send_message(
                "❌ Database connection unavailable.", ephemeral=True
            )

        await db_cog.staff_quota_profiles.update_one(
            {"_id": str(target_member.id)},
            {"$set": {"department": department_key.lower()}},
            upsert=True,
        )
        await interaction.response.send_message(
            f"✅ {target_member.mention} assigned to the `{department_key.upper()}` department."
        )

    # ------------------------------------------------------------------
    # /removedepartment
    # ------------------------------------------------------------------

    @app_commands.command(
        name="removedepartment",
        description="Remove a staff member from their department.",
    )
    @app_commands.describe(target_member="The staff member to remove from their department.")
    async def remove_department_command(
        self, interaction: discord.Interaction, target_member: discord.Member
    ):
        if (
            not interaction.user.guild_permissions.administrator
            and interaction.user.id not in self.bot.DEVELOPER_IDS
        ):
            return await interaction.response.send_message(
                "❌ Administrator permission required.", ephemeral=True
            )

        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.response.send_message(
                "❌ Database connection unavailable.", ephemeral=True
            )

        await db_cog.staff_quota_profiles.update_one(
            {"_id": str(target_member.id)},
            {"$set": {"department": None}},
        )
        await interaction.response.send_message(
            f"✅ {target_member.mention} has been removed from their department."
        )

    # ------------------------------------------------------------------
    # /listdepartments
    # ------------------------------------------------------------------

    @app_commands.command(
        name="listdepartments",
        description="List all staff members and their assigned departments.",
    )
    async def list_departments(self, interaction: discord.Interaction):

        if (
            not interaction.user.guild_permissions.administrator
            and interaction.user.id not in self.bot.DEVELOPER_IDS
        ):
            return await interaction.response.send_message(
                "❌ Administrator permission required.",
                ephemeral=True,
            )

        db_cog = self.bot.get_cog("DatabaseCog")

        if not db_cog:
            return await interaction.response.send_message(
                "❌ Database connection unavailable.",
                ephemeral=True,
            )

        profiles = await db_cog.staff_quota_profiles.find().to_list(None)

        embed = discord.Embed(
            title="📋 Department Assignments",
            color=discord.Color.blue(),
        )

        dept_map = {}

        for profile in profiles:
            department = profile.get("department")

            if not department:
                continue

            try:
                user_id = int(profile["_id"])
            except (ValueError, TypeError):
                continue

            member = interaction.guild.get_member(user_id)

            display_name = (
                member.display_name
                if member
                else f"User {user_id}"
            )

            dept_map.setdefault(department, []).append(display_name)

        if not dept_map:
            embed.description = "No department assignments found."
        else:
            for department, members in sorted(dept_map.items()):
                embed.add_field(
                    name=department.upper(),
                    value=", ".join(members) if members else "None",
                    inline=False,
                )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )


async def setup(bot):
    await bot.add_cog(StaffQuotaCog(bot))
