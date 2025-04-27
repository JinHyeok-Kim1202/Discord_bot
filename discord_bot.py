import discord
from discord import app_commands
from discord.ext import commands
import json
import os

# 1. gathering_data.json 로딩
with open("json/gathering/gathering_data.json", "r", encoding="utf-8") as f:
    GATHERING_DATA = json.load(f)

# 1. produce_data.json 로딩
with open("json/produce/metal_processing_data.json", "r", encoding="utf-8") as f:
    PRODUCE_METAL_DATA = json.load(f)
with open("json/produce/wood_processing_data.json", "r", encoding="utf-8") as f:
    PRODUCE_WOOD_DATA = json.load(f)
with open("json/produce/leather_processing_data.json", "r", encoding="utf-8") as f:
    PRODUCE_LEATHER_DATA = json.load(f)
with open("json/produce/cloth_processing_data.json", "r", encoding="utf-8") as f:
    PRODUCE_CLOTH_DATA = json.load(f)
with open("json/produce/medicine_processing_data.json", "r", encoding="utf-8") as f:
    PRODUCE_MEDICINE_DATA = json.load(f)
with open("json/produce/ingredient_processing_data.json", "r", encoding="utf-8") as f:
    PRODUCE_INGREDIENT_DATA = json.load(f)

ALL_PRODUCE_DATA = {
    **PRODUCE_METAL_DATA,
    **PRODUCE_WOOD_DATA,
    **PRODUCE_LEATHER_DATA,
    **PRODUCE_CLOTH_DATA,
    **PRODUCE_MEDICINE_DATA,
    **PRODUCE_INGREDIENT_DATA
}

# 1. trade_data.json 로딩
with open("json/trade/tirchonaill_island_shop_data.json", "r", encoding="utf-8") as f:
    TRADE_TIRCHONAILL_DATA = json.load(f)
with open("json/trade/dugal_island_shop_data.json", "r", encoding="utf-8") as f:
    TRADE_DUGAL_DATA = json.load(f)
with open("json/trade/dunbarton_shop_data.json", "r", encoding="utf-8") as f:
    TRADE_DUNBARTON_DATA = json.load(f)
with open("json/trade/colhen_shop_data.json", "r", encoding="utf-8") as f:
    TRADE_COLHEN_DATA = json.load(f)

# 물물교환 데이터 통합
ALL_TRADE_DATA = {
    **TRADE_TIRCHONAILL_DATA,
    **TRADE_DUGAL_DATA,
    **TRADE_DUNBARTON_DATA,
    **TRADE_COLHEN_DATA
}


intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

GUILD_ID = 1357686385032695828

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
async def material_gathering_autocomplete(interaction: discord.Interaction, current: str):
    choices = [
        app_commands.Choice(name=material, value=material)
        for material in GATHERING_DATA.keys()
        if current.lower() in material.lower()
    ]
    return choices[:25]

async def material_producing_autocomplete(interaction: discord.Interaction, current: str):
    choices = [
        app_commands.Choice(name=material, value=material)
        for material in ALL_PRODUCE_DATA.keys()
        if current.lower() in material.lower()
    ]
    return choices[:25]

async def material_trading_autocomplete(interaction: discord.Interaction, current: str):
    choices = [
        app_commands.Choice(name=material, value=material)
        for material in ALL_TRADE_DATA.keys()
        if current.lower() in material.lower()
    ]
    return choices[:25]

# 3. 도움말 커맨드 모음
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="명령어 모음",
        description="/채집, /제작재료, /알람시간표, /도움말 사용 방법 안내",
        color=0x00ff00
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

# 명령어 1: /도움말
#@bot.tree.command(name="도움말", description="도움말을 보여줍니다", guild=discord.Object(id=GUILD_ID))
@bot.tree.command(name="도움말", description="도움말을 보여줍니다")
async def help_cmd1(interaction: discord.Interaction):
    await help_command(interaction)

# 명령어 2: /명령어모음
#@bot.tree.command(name="명령어모음", description="명령어 리스트를 보여줍니다", guild=discord.Object(id=GUILD_ID))
@bot.tree.command(name="명령어모음", description="명령어 리스트를 보여줍니다")
async def help_cmd2(interaction: discord.Interaction):
    await help_command(interaction)

# 3. /물물교환 명령어 정의
#@bot.tree.command(name="물물교환", description="물물교환 가능한 아이템을 검색합니다", guild=discord.Object(id=GUILD_ID))
@bot.tree.command(name="물물교환", description="물물교환 가능한 아이템을 검색합니다")
@app_commands.describe(item="검색할 아이템 이름을 입력하세요")
@app_commands.autocomplete(item=material_trading_autocomplete)
async def trade_search(interaction: discord.Interaction, item: str):
    results = []
    for name, info in ALL_TRADE_DATA.items():
        if item in name:  # 아이템명에 검색어가 포함되면
            results.append((name, info))

    if not results:
        await interaction.response.send_message("❌ 해당 아이템을 찾을 수 없습니다.", ephemeral=True)
        return

    embed = discord.Embed(
        title=f"🔍 '{item}' 검색 결과",
        color=0x00ff00
    )

    for name, info in results:
        description = "------------------------\n"
        description += f"**지역:** {info.get('지역', '알 수 없음')}\n"
        description += f"**NPC:** {info.get('NPC', '알 수 없음')}\n"
        if "필요 아이템" in info:
            description += "**필요 아이템:**\n" + "\n".join(f"- {mat}" for mat in info["필요 아이템"]) + "\n"
        description += f"**구매 제한:** {info.get('구매 제한', '알 수 없음')}\n"
        description += f"**제공 아이템:** {info.get('제공 아이템', '알 수 없음')}\n"
        description += "------------------------\n"
        embed.add_field(name=name, value=description, inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)


# 4. /채집 명령어 정의
#@bot.tree.command(name="채집", description="채집할 재료를 선택하세요", guild=discord.Object(id=GUILD_ID))
@bot.tree.command(name="채집", description="채집할 재료를 선택하세요")
@app_commands.describe(material="채집할 재료 입력")
@app_commands.autocomplete(material=material_gathering_autocomplete)
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

# 5. /제작재료 명령어 정의
#@bot.tree.command(name="제작재료", description="제작할 재료를 선택하세요", guild=discord.Object(id=GUILD_ID))
@bot.tree.command(name="제작재료", description="제작할 재료를 선택하세요")
@app_commands.describe(material="제작할 재료 입력")
@app_commands.autocomplete(material=material_producing_autocomplete)
async def producing(interaction: discord.Interaction, material: str):
    if material not in ALL_PRODUCE_DATA:
        await interaction.response.send_message("❌ 해당 재료에 대한 정보를 찾을 수 없습니다.", ephemeral=True)
        return

    data = ALL_PRODUCE_DATA[material]
    item_list = ""
    if "재료" in data:
        item_list += "**재료:**\n" + "\n".join(f"- {item}" for item in data["재료"]) + "\n"
    if "시간" in data:
        item_list += f"**시간:** {data['시간']}\n"
    if "시설" in data:
        item_list += f"**시설:** {data['시설']}"

    embed = discord.Embed(
        title=f"🛠 {material} 제작 정보",
        description=item_list,
        color=0x00ff00
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)

# 6. /알람시간표 명령어 정의
#@bot.tree.command(name="알람시간표", description="필드보스 및 결계 알람 시간을 보여줍니다", guild=discord.Object(id=GUILD_ID))
@bot.tree.command(name="알람시간표", description="필드보스 및 결계 알람 시간을 보여줍니다")
async def alarm_schedule(interaction: discord.Interaction):
    content = (
        "🔔 **필드보스**: 12시, 18시, 20시, 22시\n"
        "🔸 **결계**: 12시부터 21시까지 3시간 단위 (12시, 15시, 18시, 21시)"
    )

    embed = discord.Embed(
        title="⏰ 알람 시간표",
        description=content,
        color=0x3498db
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)  # 본인에게만 보이게


bot.run(os.environ["DISCORD_BOT_TOKEN"])