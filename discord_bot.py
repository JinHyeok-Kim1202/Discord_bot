import discord
from discord import app_commands
from discord.ext import commands
import json
import os

# 1. gathering_data.json 로딩
with open("gathering_data.json", "r", encoding="utf-8") as f:
    GATHERING_DATA = json.load(f)

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

#GUILD_ID = 1357686385032695828

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands.")
    except Exception as e:
        print(e)
    # try:
    #     synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    #     print(f"Synced {len(synced)} commands for guild {GUILD_ID}.")
    # except Exception as e:
    #     print(f"Error syncing commands: {e}")

# 2. 자동완성 함수
async def material_autocomplete(interaction: discord.Interaction, current: str):
    choices = [
        app_commands.Choice(name=material, value=material)
        for material in GATHERING_DATA.keys()
        if current.lower() in material.lower()
    ]
    return choices[:25]

# 3. /채집 명령어 정의
#@bot.tree.command(name="채집", description="채집할 재료를 선택하세요", guild=discord.Object(id=GUILD_ID))
@bot.tree.command(name="채집", description="채집할 재료를 선택하세요")
@app_commands.describe(material="채집할 재료 입력")
@app_commands.autocomplete(material=material_autocomplete)
async def gathering(interaction: discord.Interaction, material: str):
    if material not in GATHERING_DATA:
        await interaction.response.send_message("❌ 해당 재료에 대한 정보를 찾을 수 없습니다.", ephemeral=True)
        return

    items = GATHERING_DATA[material]
    item_list = "\n".join(f"- {item}" for item in items)

    embed = discord.Embed(
        title=f"📦 {material} 채집 정보",
        description=item_list,
        color=0x00ff00
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)

bot.run(os.environ["DISCORD_BOT_TOKEN"])