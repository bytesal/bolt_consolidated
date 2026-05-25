import discord
from discord import app_commands
from discord.ext import commands, tasks
import datetime


DEPARTMENT_QUOTAS = {
    "board":       {"weekly_messages": 20},
    "ceo":         {"weekly_messages": 20, "weekly_hires": 1},
    "chro":        {"weekly_messages": 20, "weekly_ads_staff": 40, "weekly_ads_server": 40, "weekly_checks": 1},
    "hr":          {"weekly_messages": 15, "weekly_ads_staff": 30, "weekly_ads_server": 30, "weekly_hires": 1},
    "mod":         {"weekly_messages": 15, "weekly_adwarns_executed": 5},
    "partnership": {"weekly_messages": 5,  "weekly_ads_staff": 20, "weekly_ads_server": 20, "weekly_partnerships": 5},
}


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
            return await interaction.response.send_message("No ranks have been configured yet.", ephemeral=True)
        db_cog = interaction.client.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.response.send_message("❌ Database connection unavailable.", ephemeral=True)
        rank = await db_cog.staff_ranks.find_one({"name": self.values[0]})
        if not rank:
            return await interaction.response.send_message("❌ Rank not found in database.", ephemeral=True)
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


class StaffQuotaView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Start Shift", style=discord.ButtonStyle.green, custom_id="shift_start_btn_persistent")
    async def start_shift(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.followup.send("❌ Database connection unavailable.", ephemeral=True)
        await db_cog.staff_quota_profiles.update_one(
            {"_id": str(interaction.user.id)},
            {"$set": {"shift_start": datetime.datetime.utcnow().timestamp()}},
            upsert=True,
        )
        await interaction.followup.send("⏱️ Shift started. Your time is now being tracked.", ephemeral=True)

    @discord.ui.button(label="End Shift", style=discord.ButtonStyle.red, custom_id="shift_end_btn_persistent")
    async def end_shift(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.followup.send("❌ Database connection unavailable.", ephemeral=True)
        prof = await db_cog.staff_quota_profiles.find_one({"_id": str(interaction.user.id)})
        if not prof or not prof.get("shift_start"):
            return await interaction.followup.send("❌ You do not have an active shift running.", ephemeral=True)
        elapsed = (datetime.datetime.utcnow().timestamp() - prof["shift_start"]) / 3600.0
        await db_cog.staff_quota_profiles.update_one(
            {"_id": str(interaction.user.id)},
            {"$set": {"shift_start": None}, "$inc": {"total_shift_hours": elapsed}},
            upsert=True,
        )
        await interaction.followup.send(f"🏁 Shift ended. `{round(elapsed, 2)}` hours added to your profile.", ephemeral=True)

    @discord.ui.button(label="Check Quota", style=discord.ButtonStyle.blurple, custom_id="quota_inspect_btn_persistent")
    async def check_quota(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.followup.send("❌ Database connection unavailable.", ephemeral=True)
        prof = await db_cog.staff_quota_profiles.find_one({"_id": str(interaction.user.id)}) or {}
        dept = prof.get("department")
        if not dept or dept not in DEPARTMENT_QUOTAS:
            return await interaction.followup.send("⚠️ You have not been assigned to a department yet.", ephemeral=True)
        quotas = DEPARTMENT_QUOTAS[dept]
        embed = discord.Embed(title=f"Weekly Quota — {dept.upper()}", color=discord.Color.blue())
        for field, target in quotas.items():
            completed = prof.get(field, 0)
            label = field.replace("_", " ").title()
            status = "✅" if completed >= target else "❌"
            embed.add_field(name=f"{status} {label}", value=f"`{completed}` / `{target}`", inline=False)
        await interaction.followup.send(embed=embed, ephemeral=True)


class StaffQuotaCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.weekly_evaluation_loop.start()

    def cog_unload(self):
        self.weekly_evaluation_loop.cancel()

    async def log_quota_activity(self, user_id: int, quota_field: str, amount: int = 1):
        db_cog = self.bot.get_cog("DatabaseCog")
        if db_cog:
            await db_cog.staff_quota_profiles.update_one(
                {"_id": str(user_id)},
                {"$inc": {quota_field: amount}},
                upsert=True,
            )

    @tasks.loop(minutes=5.0)
    async def weekly_evaluation_loop(self):
        now = datetime.datetime.utcnow()
        if now.weekday() == 5 and now.hour == 23 and now.minute >= 55:
            db_cog = self.bot.get_cog("DatabaseCog")
            if not db_cog:
                return
            async for profile in db_cog.staff_quota_profiles.find():
                u_id = profile["_id"]
                dept = profile.get("department")
                if dept and dept in DEPARTMENT_QUOTAS:
                    requirements = DEPARTMENT_QUOTAS[dept]
                    missed = any(profile.get(field, 0) < target for field, target in requirements.items())
                    if missed:
                        await db_cog.staff_quota_profiles.update_one({"_id": u_id}, {"$inc": {"total_strikes": 1}})
                await db_cog.staff_quota_profiles.update_one(
                    {"_id": u_id},
                    {"$set": {
                        "weekly_messages": 0,
                        "weekly_ads_staff": 0,
                        "weekly_ads_server": 0,
                        "weekly_hires": 0,
                        "weekly_mod_actions": 0,
                        "weekly_partnerships": 0,
                        "weekly_checks": 0,
                        "weekly_adwarns_executed": 0,
                    }}
                )

    @weekly_evaluation_loop.before_loop
    async def before_weekly_loop(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="setdepartment", description="Assign a staff member to a department.")
    @app_commands.describe(target_member="The staff member to assign.", department_key=f"Department name. Options: {', '.join(DEPARTMENT_QUOTAS.keys())}")
    async def set_department_command(self, interaction: discord.Interaction, target_member: discord.Member, department_key: str):
        if not interaction.user.guild_permissions.administrator and interaction.user.id not in self.bot.DEVELOPER_IDS:
            return await interaction.response.send_message("❌ Administrator permission required.", ephemeral=True)
        if department_key.lower() not in DEPARTMENT_QUOTAS:
            valid = ", ".join(f"`{k}`" for k in DEPARTMENT_QUOTAS)
            return await interaction.response.send_message(f"❌ Invalid department. Valid options: {valid}", ephemeral=True)
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.response.send_message("❌ Database connection unavailable.", ephemeral=True)
        await db_cog.staff_quota_profiles.update_one(
            {"_id": str(target_member.id)},
            {"$set": {"department": department_key.lower()}},
            upsert=True,
        )
        await interaction.response.send_message(f"✅ {target_member.mention} assigned to the `{department_key.upper()}` department.")

    @app_commands.command(name="removedepartment", description="Remove a staff member from their department.")
    @app_commands.describe(target_member="The staff member to remove from their department.")
    async def remove_department_command(self, interaction: discord.Interaction, target_member: discord.Member):
        if not interaction.user.guild_permissions.administrator and interaction.user.id not in self.bot.DEVELOPER_IDS:
            return await interaction.response.send_message("❌ Administrator permission required.", ephemeral=True)
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.response.send_message("❌ Database connection unavailable.", ephemeral=True)
        await db_cog.staff_quota_profiles.update_one(
            {"_id": str(target_member.id)},
            {"$set": {"department": None}},
        )
        await interaction.response.send_message(f"✅ {target_member.mention} has been removed from their department.")

    @app_commands.command(name="listdepartments", description="List all staff members and their assigned departments.")
    async def list_departments(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator and interaction.user.id not in self.bot.DEVELOPER_IDS:
            return await interaction.response.send_message("❌ Administrator permission required.", ephemeral=True)
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.response.send_message("❌ Database connection unavailable.", ephemeral=True)
        profiles = await db_cog.staff_quota_profiles.find().to_list(None)
        embed = discord.Embed(title="📋 Department Assignments", color=discord.Color.blue())
        dept_map = {}
        for p in profiles:
            dept = p.get("department")
            if dept:
                user_id = int(p["_id"])
                member = interaction.guild.get_member(user_id)
                name = member.display_name if member else f"User {user_id}"
                dept_map.setdefault(dept, []).append(name)
        if not dept_map:
            embed.description = "No department assignments found."
        else:
            for dept, members in dept_map.items():
                embed.add_field(name=dept.upper(), value=", ".join(members) or "None", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="addrank", description="Create a new staff rank profile.")
    @app_commands.describe(name="The rank name.", emoji="An emoji to represent this rank.", description="A brief description of the rank.")
    async def add_rank_command(self, interaction: discord.Interaction, name: str, emoji: str, description: str):
        if not interaction.user.guild_permissions.administrator and interaction.user.id not in self.bot.DEVELOPER_IDS:
            return await interaction.response.send_message("❌ Administrator permission required.", ephemeral=True)
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.response.send_message("❌ Database connection unavailable.", ephemeral=True)
        await db_cog.staff_ranks.update_one(
            {"name": name},
            {"$set": {"emoji": emoji, "description": description, "duties": []}},
            upsert=True,
        )
        await interaction.response.send_message(f"✅ Rank **{name}** created successfully.")

    @app_commands.command(name="addduty", description="Add a responsibility to an existing staff rank.")
    @app_commands.describe(rank_name="The name of the rank to update.", responsibility_text="The duty or responsibility to add.")
    async def add_duty_command(self, interaction: discord.Interaction, rank_name: str, responsibility_text: str):
        if not interaction.user.guild_permissions.administrator and interaction.user.id not in self.bot.DEVELOPER_IDS:
            return await interaction.response.send_message("❌ Administrator permission required.", ephemeral=True)
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.response.send_message("❌ Database connection unavailable.", ephemeral=True)
        result = await db_cog.staff_ranks.update_one(
            {"name": rank_name},
            {"$push": {"duties": responsibility_text}},
        )
        if result.matched_count == 0:
            return await interaction.response.send_message(f"❌ Rank `{rank_name}` not found.", ephemeral=True)
        await interaction.response.send_message(f"✅ Duty added to rank **{rank_name}**.")

    @app_commands.command(name="poststaffdropdown", description="Post the staff ranks overview dropdown in the current channel.")
    async def post_staff_dropdown(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator and interaction.user.id not in self.bot.DEVELOPER_IDS:
            return await interaction.response.send_message("❌ Administrator permission required.", ephemeral=True)
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.response.send_message("❌ Database connection unavailable.", ephemeral=True)
        ranks_map = {}
        async for r in db_cog.staff_ranks.find():
            ranks_map[r["name"]] = r.get("description", "")
        if not ranks_map:
            ranks_map["No Ranks Configured"] = "Please add ranks using /addrank."
        await interaction.response.send_message("📌 **Staff Ranks Overview**", view=RanksDropdownView(ranks_map))

    @app_commands.command(name="deployquotamatrix", description="Deploy the staff shift and quota tracking dashboard.")
    async def deploy_quota_matrix(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator and interaction.user.id not in self.bot.DEVELOPER_IDS:
            return await interaction.response.send_message("❌ Administrator permission required.", ephemeral=True)
        await interaction.response.send_message("💼 **Staff Shift & Quota Dashboard**", view=StaffQuotaView(self.bot))


async def setup(bot):
    await bot.add_cog(StaffQuotaCog(bot))
