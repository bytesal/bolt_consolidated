import os
import discord
from discord import app_commands
from discord.ext import commands, tasks
import datetime

DEPARTMENT_QUOTAS = {
    "board": {"weekly_messages": 20},
    "ceo": {"weekly_messages": 20, "weekly_hires": 1},
    "chro": {"weekly_messages": 20, "weekly_ads_staff": 40, "weekly_ads_server": 40, "weekly_checks": 1},
    "hr": {"weekly_messages": 15, "weekly_ads_staff": 30, "weekly_ads_server": 30, "weekly_hires": 1},
    "mod": {"weekly_messages": 15, "weekly_adwarns_executed": 5},
    "partnership": {"weekly_messages": 5, "weekly_ads_staff": 20, "weekly_ads_server": 20, "weekly_partnerships": 5}
}

class StaffRanksDropdown(discord.ui.Select):
    def __init__(self, ranks_dict):
        options = [discord.SelectOption(label=name, description=f"Review duties for {name}") for name in list(ranks_dict.keys())[:25]]
        if not options:
            options = [discord.SelectOption(label="System Initialization Clear", value="empty")]
        super().__init__(placeholder="Select a staff position matrix layout to view responsibilities...", options=options, custom_id="staff_ranks_dropdown_select_persistent")

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "empty":
            return await interaction.response.send_message("No rank options available inside data pools.", ephemeral=True)
        
        db_cog = interaction.client.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.response.send_message("❌ Core DB Connection Unavailable.", ephemeral=True)
            
        rank = await db_cog.staff_ranks.find_one({"name": self.values[0]})
        if not rank:
            return await interaction.response.send_message("Matrix lookup trace mapping error.", ephemeral=True)

        embed = discord.Embed(title=f"Position Briefing: {rank['name']}", description=rank.get("description", "No summary attached."), color=discord.Color.purple())
        duties = rank.get("duties", [])
        if duties:
            embed.add_field(name="📋 Core Requirements", value="\n".join([f"• {d}" for d in duties]), inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

class RanksDropdownView(discord.ui.View):
    def __init__(self, ranks_dict):
        super().__init__(timeout=None)
        self.add_item(StaffRanksDropdown(ranks_dict))

class StaffQuotaView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Begin Shift Session", style=discord.ButtonStyle.green, custom_id="shift_start_btn_persistent")
    async def start_shift(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.followup.send("❌ Core DB Connection Unavailable.", ephemeral=True)
            
        u_id = str(interaction.user.id)
        await db_cog.staff_quota_profiles.update_one(
            {"_id": u_id},
            {"$set": {"shift_start": datetime.datetime.utcnow().timestamp()}},
            upsert=True
        )
        await interaction.followup.send("⏱️ Duty cycle metrics tracking initialization logged successfully.", ephemeral=True)

    @discord.ui.button(label="Conclude Shift Session", style=discord.ButtonStyle.red, custom_id="shift_end_btn_persistent")
    async def end_shift(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.followup.send("❌ Core DB Connection Unavailable.", ephemeral=True)
            
        u_id = str(interaction.user.id)
        prof = await db_cog.staff_quota_profiles.find_one({"_id": u_id})
        if not prof or not prof.get("shift_start"):
            return await interaction.followup.send("❌ Transmission Error: No active shift tracking frame registered.", ephemeral=True)
            
        elapsed = (datetime.datetime.utcnow().timestamp() - prof["shift_start"]) / 3600.0
        await db_cog.staff_quota_profiles.update_one(
            {"_id": u_id},
            {"$set": {"shift_start": None}, "$inc": {"total_shift_hours": elapsed}},
            upsert=True
        )
        await interaction.followup.send(f"🏁 Session terminated cleanly. `{round(elapsed, 2)}` operational performance metrics added to profile record.", ephemeral=True)

    @discord.ui.button(label="Inspect Current Quota Status", style=discord.ButtonStyle.blurple, custom_id="quota_inspect_btn_persistent")
    async def check_quota(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.followup.send("❌ Core DB Connection Unavailable.", ephemeral=True)
            
        prof = await db_cog.staff_quota_profiles.find_one({"_id": str(interaction.user.id)}) or {}
        dept = prof.get("department")
        if not dept or dept not in DEPARTMENT_QUOTAS:
            return await interaction.followup.send("⚠️ Operational Profile Alert: Specific division alignment missing.", ephemeral=True)
            
        quotas = DEPARTMENT_QUOTAS[dept]
        embed = discord.Embed(title=f"Workload Tracking Framework Matrix: {dept.upper()}", color=discord.Color.blue())
        for target_field, objective_value in quotas.items():
            completed = prof.get(target_field, 0)
            embed.add_field(name=target_field.replace("_", " ").title(), value=f"`{completed}` / `{objective_value}` units processed completed metrics.", inline=False)
            
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
                upsert=True
            )

    @tasks.loop(minutes=5.0)
    async def weekly_evaluation_loop(self):
        now = datetime.datetime.utcnow()
        if now.weekday() == 5 and now.hour == 23 and now.minute >= 55:
            db_cog = self.bot.get_cog("DatabaseCog")
            if not db_cog:
                return
                
            cursor = db_cog.staff_quota_profiles.find()
            async for member_profile in cursor:
                u_id = member_profile["_id"]
                dept = member_profile.get("department")
                
                if dept and dept in DEPARTMENT_QUOTAS:
                    requirements = DEPARTMENT_QUOTAS[dept]
                    passed = True
                    for matrix, check_value in requirements.items():
                        if member_profile.get(matrix, 0) < check_value:
                            passed = False
                            break
                    
                    if not passed:
                        await db_cog.staff_quota_profiles.update_one(
                            {"_id": u_id},
                            {"$inc": {"total_strikes": 1}}
                        )
                
                await db_cog.staff_quota_profiles.update_one(
                    {"_id": u_id},
                    {"$set": {
                        "weekly_messages": 0, "weekly_ads_staff": 0, "weekly_ads_server": 0,
                        "weekly_hires": 0, "weekly_mod_actions": 0, "weekly_partnerships": 0,
                        "weekly_checks": 0, "weekly_adwarns_executed": 0
                    }}
                )

    @app_commands.command(name="setdepartment", description="Assign a specific operational department framework onto a target staff member footprint.")
    @app_commands.describe(
        target_member="The target staff member to bind to the division framework.",
        department_key="Division designation selection matrix block key."
    )
    async def set_department_command(self, interaction: discord.Interaction, target_member: discord.Member, department_key: str):
        if not interaction.user.guild_permissions.administrator and interaction.user.id not in self.bot.DEVELOPER_IDS:
            return await interaction.response.send_message("❌ Authorization Failed.", ephemeral=True)
            
        if department_key.lower() not in DEPARTMENT_QUOTAS:
            return await interaction.response.send_message(f"❌ Invalid selection block. Pick from: `{', '.join(list(DEPARTMENT_QUOTAS.keys()))}`", ephemeral=True)
            
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.response.send_message("❌ Core DB Connection Unavailable.", ephemeral=True)

        await db_cog.staff_quota_profiles.update_one(
            {"_id": str(target_member.id)},
            {"$set": {"department": department_key.lower()}},
            upsert=True
        )
        await interaction.response.send_message(f"✅ User assigned mapping profile to: `{department_key.upper()}` division.")

    @app_commands.command(name="removedepartment", description="Cleanly remove a target member from all specialized staff department assignments.")
    @app_commands.describe(target_member="The target staff member profile to detach from division mappings.")
    async def remove_department_command(self, interaction: discord.Interaction, target_member: discord.Member):
        if not interaction.user.guild_permissions.administrator and interaction.user.id not in self.bot.DEVELOPER_IDS:
            return await interaction.response.send_message("❌ Authorization Failed.", ephemeral=True)
            
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.response.send_message("❌ Core DB Connection Unavailable.", ephemeral=True)

        await db_cog.staff_quota_profiles.update_one(
            {"_id": str(target_member.id)},
            {"$set": {"department": None}}
        )
        await interaction.response.send_message(f"✅ Cleanly removed {target_member.mention} from all department assignments.")

    @app_commands.command(name="addrank", description="Create a system profile reference log for a new staff rank structure configuration.")
    @app_commands.describe(
        name="The explicit name designation for the new structural rank.",
        emoji="The localized emoji character to bind to visual listings.",
        description="The summary or layout context information text payload."
    )
    async def add_rank_command(self, interaction: discord.Interaction, name: str, emoji: str, description: str):
        if not interaction.user.guild_permissions.administrator and interaction.user.id not in self.bot.DEVELOPER_IDS:
            return await interaction.response.send_message("❌ Access Restricted.", ephemeral=True)
            
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.response.send_message("❌ Core DB Connection Unavailable.", ephemeral=True)

        await db_cog.staff_ranks.update_one({"name": name}, {"$set": {"emoji": emoji, "description": description, "duties": []}}, upsert=True)
        await interaction.response.send_message(f"✅ Created system profile reference for rank: **{name}**")

    @app_commands.command(name="addduty", description="Link explicit requirement framework updates and responsibilities onto an existing rank configuration.")
    @app_commands.describe(
        rank_name="The explicit name designation of the target rank profile to update.",
        responsibility_text="The individual duty requirement text string payload to append."
    )
    async def add_duty_command(self, interaction: discord.Interaction, rank_name: str, responsibility_text: str):
        if not interaction.user.guild_permissions.administrator and interaction.user.id not in self.bot.DEVELOPER_IDS:
            return await interaction.response.send_message("❌ Access Restricted.", ephemeral=True)
            
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.response.send_message("❌ Core DB Connection Unavailable.", ephemeral=True)

        await db_cog.staff_ranks.update_one({"name": rank_name}, {"$push": {"duties": responsibility_text}})
        await interaction.response.send_message(f"✅ Linked requirements structure framework updates onto rank: {rank_name}")

    @app_commands.command(name="poststaffdropdown", description="Deploy the structured visual dropdown matrix interface overview for staff rank selections.")
    async def post_staff_dropdown(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator and interaction.user.id not in self.bot.DEVELOPER_IDS:
            return await interaction.response.send_message("❌ Access Restricted.", ephemeral=True)
            
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.response.send_message("❌ Core DB Connection Unavailable.", ephemeral=True)

        cursor = db_cog.staff_ranks.find()
        ranks_map = {}
        async for r in cursor:
            ranks_map[r["name"]] = r.get("description", "")
            
        if not ranks_map:
            ranks_map["Default Staff Initialization Setup"] = "Pending profile logs assignment configurations."
            
        await interaction.response.send_message("📌 **Staff Operations Structural Assignment Context Overview**", view=RanksDropdownView(ranks_map))

    @app_commands.command(name="deployquotamatrix", description="Deploy the interactive button engine terminal dashboard for staff shifts and quotas tracking.")
    async def deploy_quota_matrix(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator and interaction.user.id not in self.bot.DEVELOPER_IDS:
            return await interaction.response.send_message("❌ Access Metrics Authentication Fault.", ephemeral=True)
            
        await interaction.response.send_message("💼 **Staff Interface Resource Terminal Controls Engine**", view=StaffQuotaView(self.bot))

async def setup(bot):
    await bot.add_cog(StaffQuotaCog(bot))
