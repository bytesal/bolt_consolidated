import discord
from discord import app_commands
from discord.ext import commands, tasks
import datetime
import os

# Precise quotas requested via source structure consolidation and customization instructions
DEPARTMENT_QUOTAS = {
    "board": {"weekly_messages": 20},
    "ceo": {"weekly_messages": 20, "weekly_hires": 1},
    "chro": {"weekly_messages": 20, "weekly_ads_staff": 40, "weekly_ads_server": 40, "weekly_checks": 1},
    "hr": {"weekly_messages": 15, "weekly_ads_staff": 30, "weekly_ads_server": 30, "weekly_hires": 1},
    "mod": {"weekly_messages": 15, "weekly_adwarns_executed": 5}, # Adjusted strict metric replacement criteria
    "partnership": {"weekly_messages": 5, "weekly_ads_staff": 20, "weekly_ads_server": 20, "weekly_partnerships": 5}
}

class StaffRanksDropdown(discord.ui.Select):
    def __init__(self, ranks_dict):
        options = [discord.SelectOption(label=name, description=f"Review duties for {name}") for name in list(ranks_dict.keys())[:25]]
        if not options:
            options = [discord.SelectOption(label="System Initialization Clear", value="empty")]
        super().__init__(placeholder="Select a staff position matrix layout to view responsibilities...", options=options, custom_id="staff_ranks_dropdown_select")

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "empty":
            return await interaction.response.send_message("No rank options available inside data pools.", ephemeral=True)
        db_cog = interaction.client.get_cog("DatabaseCog")
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

    @discord.ui.button(label="Begin Shift Session", style=discord.ButtonStyle.green, custom_id="shift_start_btn")
    async def start_shift(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        db_cog = self.bot.get_cog("DatabaseCog")
        u_id = str(interaction.user.id)
        
        await db_cog.staff_quota_profiles.update_one(
            {"_id": u_id},
            {"$set": {"shift_start": datetime.datetime.utcnow().timestamp()}},
            upsert=True
        )
        await interaction.followup.send("⏱️ Duty cycle metrics tracking initialization logged successfully.", ephemeral=True)

    @discord.ui.button(label="Conclude Shift Session", style=discord.ButtonStyle.red, custom_id="shift_end_btn")
    async def end_shift(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        db_cog = self.bot.get_cog("DatabaseCog")
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

    @discord.ui.button(label="Inspect Current Quota Status", style=discord.ButtonStyle.blurple, custom_id="quota_inspect_btn")
    async def check_quota(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        db_cog = self.bot.get_cog("DatabaseCog")
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
        # Evaluate terminal calculations perfectly on Saturday at 23:59 target alignment frames
        if now.weekday() == 5 and now.hour == 23 and now.minute >= 55:
            db_cog = self.bot.get_cog("DatabaseCog")
            if not db_cog:
                return
                
            cursor = db_cog.staff_quota_profiles.find()
            async for member_profile in cursor:
                u_id = member_profile["_id"]
                dept = member_profile.get("department")
                
                # Evaluation Engine: Check metrics parameters if mapped safely
                if dept and dept in DEPARTMENT_QUOTAS:
                    requirements = DEPARTMENT_QUOTAS[dept]
                    passed = True
                    for matrix, check_value in requirements.items():
                        if member_profile.get(matrix, 0) < check_value:
                            passed = False
                            break
                    
                    # Manual management modification validation requirement compliance:
                    # Increment strike tracking logs only. Do not perform automated role stripping operations.
                    if not passed:
                        await db_cog.staff_quota_profiles.update_one(
                            {"_id": u_id},
                            {"$inc": {"total_strikes": 1}}
                        )
                
                # Clear standard parameters reset structures cleanly
                await db_cog.staff_quota_profiles.update_one(
                    {"_id": u_id},
                    {"$set": {
                        "weekly_messages": 0, "weekly_ads_staff": 0, "weekly_ads_server": 0,
                        "weekly_hires": 0, "weekly_mod_actions": 0, "weekly_partnerships": 0,
                        "weekly_checks": 0, "weekly_adwarns_executed": 0
                    }}
                )

    @commands.command(name="setdepartment")
    async def set_department_command(self, ctx, target_member: discord.Member, department_key: str):
        if not ctx.author.guild_permissions.administrator and ctx.author.id not in self.bot.DEVELOPER_IDS:
            return await ctx.send("❌ Authorization Failed.")
        if department_key.lower() not in DEPARTMENT_QUOTAS:
            return await ctx.send(f"❌ Invalid selection block. Pick from: `{', '.join(list(DEPARTMENT_QUOTAS.keys()))}`")
            
        db_cog = self.bot.get_cog("DatabaseCog")
        await db_cog.staff_quota_profiles.update_one(
            {"_id": str(target_member.id)},
            {"$set": {"department": department_key.lower()}},
            upsert=True
        )
        await ctx.send(f"✅ User assigned mapping profile to: `{department_key.upper()}` division.")

    @commands.command(name="removedepartment")
    async def remove_department_command(self, ctx, target_member: discord.Member):
        """Custom Modification Requirement 1: Dedicated option to cleanly remove people from departments"""
        if not ctx.author.guild_permissions.administrator and ctx.author.id not in self.bot.DEVELOPER_IDS:
            return await ctx.send("❌ Authorization Failed.")
            
        db_cog = self.bot.get_cog("DatabaseCog")
        await db_cog.staff_quota_profiles.update_one(
            {"_id": str(target_member.id)},
            {"$set": {"department": None}}
        )
        await ctx.send(f"✅ Cleanly removed {target_member.mention} from all department assignments.")

    @commands.command(name="addrank")
    async def add_rank_command(self, ctx, name: str, emoji: str, *, description: str):
        if not ctx.author.guild_permissions.administrator and ctx.author.id not in self.bot.DEVELOPER_IDS:
            return await ctx.send("❌ Access Restressed.")
        db_cog = self.bot.get_cog("DatabaseCog")
        await db_cog.staff_ranks.update_one({"name": name}, {"$set": {"emoji": emoji, "description": description, "duties": []}}, upsert=True)
        await ctx.send(f"✅ Created system profile reference for rank: **{name}**")

    @commands.command(name="addduty")
    async def add_duty_command(self, ctx, rank_name: str, *, responsibility_text: str):
        if not ctx.author.guild_permissions.administrator and ctx.author.id not in self.bot.DEVELOPER_IDS:
            return await ctx.send("❌ Access Restressed.")
        db_cog = self.bot.get_cog("DatabaseCog")
        await db_cog.staff_ranks.update_one({"name": rank_name}, {"$push": {"duties": responsibility_text}})
        await ctx.send(f"✅ Linked requirements structure framework updates onto rank: {rank_name}")

    @commands.command(name="poststaffdropdown")
    async def post_staff_dropdown(self, ctx):
        if not ctx.author.guild_permissions.administrator and ctx.author.id not in self.bot.DEVELOPER_IDS:
            return await ctx.send("❌ Access Restressed.")
        db_cog = self.bot.get_cog("DatabaseCog")
        cursor = db_cog.staff_ranks.find()
        ranks_map = {}
        async for r in cursor:
            ranks_map[r["name"]] = r.get("description", "")
            
        if not ranks_map:
            ranks_map["Default Staff Initialization Setup"] = "Pending profile logs assignment configurations."
            
        await ctx.send("📌 **Staff Operations Structural Assignment Context Overview**", view=RanksDropdownView(ranks_map))

    @commands.command(name="deployquotamatrix")
    async def deploy_quota_matrix(self, ctx):
        if not ctx.author.guild_permissions.administrator and ctx.author.id not in self.bot.DEVELOPER_IDS:
            return await ctx.send("❌ Access Metrics Authentication Fault.")
        await ctx.send("💼 **Staff Interface Resource Terminal Controls Engine**", view=StaffQuotaView(self.bot))

async def setup(bot):
    await bot.add_cog(StaffQuotaCog(bot))
