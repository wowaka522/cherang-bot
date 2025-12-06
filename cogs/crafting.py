import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional

from utils.raphael import (
    ensure_raphael_ready,
    get_user_stats,
    set_user_stats,
    search_recipe,
    search_meal_items,
    search_potion_items,
    get_ingredients,
    is_hq_candidate,
    solve_macro,
    split_macros,
)

# ======================================================
# HQ Modal
# ======================================================
class HQModal(discord.ui.Modal, title="⭐ HQ 재료 개수 입력"):
    def __init__(self, cog, recipe_id, recipe_name, stats, food, potion, slots):
        super().__init__()
        self.cog = cog
        self.recipe_id = recipe_id
        self.recipe_name = recipe_name
        self.stats = stats
        self.food = food
        self.potion = potion
        self.slots = slots

        self.inputs = []
        for ing in self.slots:
            ti = discord.ui.TextInput(
                label=f"{ing['name']} (최대 {ing['amount']})",
                placeholder="0",
                required=False,
                max_length=3,
            )
            self.inputs.append(ti)
            self.add_item(ti)

    async def on_submit(self, interaction: discord.Interaction):
        hq_list = []
        for ti, ing in zip(self.inputs, self.slots):
            raw = ti.value.strip()
            if not raw:
                hq_list.append(0)
                continue
            try:
                v = int(raw)
            except ValueError:
                v = 0
            v = max(0, min(v, ing["amount"]))
            hq_list.append(v)

        await self.cog.generate_macro(
            interaction,
            self.recipe_id,
            self.recipe_name,
            self.stats,
            self.food,
            self.potion,
            hq_list
        )


# ======================================================
# Select Menu (직업 변경)
# ======================================================
class JobSelect(discord.ui.Select):
    def __init__(self, cog, user_id, jobs):
        self.cog = cog
        self.user_id = user_id

        options = [
            discord.SelectOption(label=job)
            for job in jobs
        ]
        super().__init__(
            placeholder="변경할 직업을 선택하세요",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        uid = self.user_id
        db = get_user_stats(uid)
        job = self.values[0]
        db["last_job"] = job
        set_user_stats(uid, db)
        await interaction.response.send_message(
            f"✔ 기본 직업이 `{job}` 으로 변경되었습니다.",
            ephemeral=True,
        )


class JobManageView(discord.ui.View):
    def __init__(self, cog, uid):
        super().__init__(timeout=180)
        self.cog = cog
        self.uid = uid
        user_data = get_user_stats(uid)
        jobs = list(user_data.get("jobs", {}).keys())

        if jobs:
            self.add_item(JobSelect(cog, uid, jobs))

        self.add_item(NewJobButton(cog, uid))
        if jobs:
            self.add_item(DeleteJobButton(cog, uid))


class NewJobButton(discord.ui.Button):
    def __init__(self, cog, uid):
        super().__init__(label="새 직업 추가", style=discord.ButtonStyle.primary)
        self.cog = cog
        self.uid = uid

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(StatsModal(self.cog, self.uid))


class DeleteJobButton(discord.ui.Button):
    def __init__(self, cog, uid):
        super().__init__(label="삭제", style=discord.ButtonStyle.danger)
        self.cog = cog
        self.uid = uid

    async def callback(self, interaction: discord.Interaction):
        db = get_user_stats(self.uid)
        last = db.get("last_job")
        if not last:
            return await interaction.response.send_message(
                "❌ 삭제할 직업이 없습니다.",
                ephemeral=True,
            )
        jobs = db.get("jobs", {})
        jobs.pop(last, None)
        db["jobs"] = jobs
        db["last_job"] = next(iter(jobs.keys()), None)
        set_user_stats(self.uid, db)
        await interaction.response.send_message(
            f"🗑 `{last}` 직업 삭제 완료!",
            ephemeral=True,
        )


# ======================================================
# Stats Modal (직업 추가/수정)
# ======================================================
class StatsModal(discord.ui.Modal, title="⚙ 직업 스탯 등록"):
    job = discord.ui.TextInput(label="직업 이름", placeholder="예: 목수")
    craft = discord.ui.TextInput(label="작업 숙련도", placeholder="4000")
    control = discord.ui.TextInput(label="가공 숙련도", placeholder="3800")
    cp = discord.ui.TextInput(label="CP", placeholder="580")
    level = discord.ui.TextInput(label="레벨", placeholder="90")

    def __init__(self, cog, uid):
        super().__init__()
        self.cog = cog
        self.uid = uid

    async def on_submit(self, interaction: discord.Interaction):
        uid = self.uid
        try:
            data = {
                "craft": int(self.craft.value),
                "control": int(self.control.value),
                "cp": int(self.cp.value),
                "job_level": int(self.level.value),
            }
        except ValueError:
            return await interaction.response.send_message(
                "❌ 숫자만 입력해주세요",
                ephemeral=True,
            )

        job_name = self.job.value.strip()
        if not job_name:
            return await interaction.response.send_message(
                "❌ 직업명을 입력해주세요",
                ephemeral=True,
            )

        u = get_user_stats(uid)
        jobs = u.get("jobs", {})
        jobs[job_name] = data
        u["jobs"] = jobs
        u["last_job"] = job_name
        set_user_stats(uid, u)

        await interaction.response.send_message(
            f"✔ `{job_name}` 스탯 등록 완료!",
            ephemeral=True,
        )


# ======================================================
# Crafting Cog
# ======================================================
class CraftingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def generate_macro(self, interaction, recipe_id, recipe_name, stats, food, potion, hq_list):
        actions, err = solve_macro(recipe_id, stats, food, potion, hq_list)
        if err:
            return await interaction.response.send_message(
                f"❌ 오류\n```txt\n{err}\n```",
                ephemeral=True,
            )

        chunks = split_macros(actions)
        await interaction.response.send_message(
            f"📜 Macro #1\n```txt\n{chunks[0]}\n```",
            ephemeral=True,
        )
        for idx, block in enumerate(chunks[1:], start=2):
            await interaction.followup.send(
                f"📜 Macro #{idx}\n```txt\n{block}\n```",
                ephemeral=True,
            )

    # ----------------------- Slash: 제작 -----------------------
    @app_commands.command(name="제작", description="FFXIV 제작 매크로를 생성합니다.")
    async def cmd_craft(
        self,
        interaction: discord.Interaction,
        recipe: str,
        food: Optional[str] = None,
        potion: Optional[str] = None,
    ):
        uid = str(interaction.user.id)
        user_data = get_user_stats(uid)
        if not user_data or not user_data.get("jobs"):
            return await interaction.response.send_message(
                "⚠ 등록된 직업이 없습니다. `/상태`에서 직업을 추가해주세요.",
                ephemeral=True,
            )

        job_name = user_data.get("last_job")
        stats = user_data["jobs"][job_name]

        try:
            recipe_id = int(recipe)
        except ValueError:
            return await interaction.response.send_message("❌ 레시피 오류", ephemeral=True)

        ings = get_ingredients(recipe_id)
        candidates = [i for i in ings if is_hq_candidate(i["name"])][:5]

        if not candidates:
            await self.generate_macro(
                interaction, recipe_id, recipe, stats, food, potion, None
            )
        else:
            await interaction.response.send_modal(
                HQModal(self, recipe_id, recipe, stats, food, potion, candidates)
            )

    # 자동완성
    @cmd_craft.autocomplete("recipe")
    async def ac_recipe(self, interaction, current: str):
        return [
            app_commands.Choice(name=r["name"], value=str(r["id"]))
            for r in search_recipe(current)[:25]
        ]

    @cmd_craft.autocomplete("food")
    async def ac_food(self, interaction, current: str):
        return [
            app_commands.Choice(name=name, value=str(iid))
            for iid, name in search_meal_items(current)
        ]

    @cmd_craft.autocomplete("potion")
    async def ac_potion(self, interaction, current: str):
        return [
            app_commands.Choice(name=name, value=str(iid))
            for iid, name in search_potion_items(current)
        ]

    # ----------------------- Slash: 상태 -----------------------
    @app_commands.command(name="상태", description="제작 직업/스탯 관리")
    async def cmd_status(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        u = get_user_stats(uid)
        jobs = u.get("jobs", {})

        if not jobs:
            view = JobManageView(self, uid)
            return await interaction.response.send_message(
                "등록된 직업이 없습니다!",
                view=view,
                ephemeral=True,
            )

        last = u.get("last_job")
        stats = jobs[last]

        text = (
            f"📌 **제작 상태**\n"
            f"{last} (Lv{stats['job_level']})\n"
            f"작업: {stats['craft']}\n"
            f"가공: {stats['control']}\n"
            f"CP: {stats['cp']}\n"
        )

        view = JobManageView(self, uid)
        await interaction.response.send_message(text, view=view, ephemeral=True)


# ======================================================
async def setup(bot):
    ensure_raphael_ready()
    await bot.add_cog(CraftingCog(bot))