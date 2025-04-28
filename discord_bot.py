import discord
from discord import app_commands
from discord.ext import commands, tasks
import json
import os
import threading
import time
import requests
from fastapi import FastAPI
import uvicorn
import asyncio
import datetime
import sys

# dev / prod 모드 결정
if "dev" in sys.argv:
    CONFIG_FILE = "json/config/config_dev.json"
    dev_mode = True
else:
    CONFIG_FILE = "json/config/config_prod.json"
    dev_mode = False

# config 불러오기
with open(CONFIG_FILE, "r", encoding="utf-8") as f:
    config_data = json.load(f)

TOKEN = config_data["TOKEN"]
GUILD_ID = config_data["GUILD_ID"]
command_guild = discord.Object(id=GUILD_ID) if dev_mode else None

# 파일 로딩
ROLE_DATA_FILE = "json/alarm/alarm_roles.json"
ALARM_CONFIG_FILE = "json/alarm/alarm_config.json"
ALARM_DATA_FILE = "json/alarm/alarm_users.json"

if os.path.exists(ROLE_DATA_FILE):
    with open(ROLE_DATA_FILE, "r", encoding="utf-8") as f:
        role_ids = json.load(f)
else:
    role_ids = {}

if os.path.exists(ALARM_CONFIG_FILE):
    with open(ALARM_CONFIG_FILE, "r", encoding="utf-8") as f:
        alarm_config = json.load(f)
else:
    alarm_config = {"alarm_channel_id": None}

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

# 역할 자동 생성 함수
async def setup_alarm_roles(guild: discord.Guild):
    if str(guild.id) not in role_ids:
        role_ids[str(guild.id)] = {"결계": {}, "필드보스": {}}

    for hour in [0, 3, 6, 9, 12, 15, 18, 21]:
        name = f"결계 {hour}시"
        role = discord.utils.get(guild.roles, name=name)
        if not role:
            role = await guild.create_role(name=name)
        role_ids[str(guild.id)]["결계"][str(hour)] = [role.id]

    for hour in [12, 18, 20, 22]:
        name = f"필보 {hour}시"
        role = discord.utils.get(guild.roles, name=name)
        if not role:
            role = await guild.create_role(name=name)
        role_ids[str(guild.id)]["필드보스"][str(hour)] = [role.id]

    with open(ROLE_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(role_ids, f, ensure_ascii=False, indent=4)

    print(f"✅ {guild.name} 역할 세팅 완료")

# 알람 설정 View
class AlarmSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(AlarmSelectMenu())

class AlarmSelectMenu(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="결계 알람 설정", value="barrier"),
            discord.SelectOption(label="필드보스 알람 설정", value="boss")
        ]
        super().__init__(placeholder="설정할 알람 종류를 선택하세요", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        selection = self.values[0]
        if selection == "barrier":
            await interaction.response.send_message(view=BarrierSelectView(), ephemeral=True)
        else:
            await interaction.response.send_message(view=BossSelectView(), ephemeral=True)

class BarrierSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(BarrierSelect())

class BarrierSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=f"{hour}시", value=str(hour)) for hour in [0, 3, 6, 9, 12, 15, 18, 21]
        ]
        super().__init__(placeholder="결계 시간 선택", min_values=1, max_values=8, options=options)

    async def callback(self, interaction: discord.Interaction):
        added = []
        for hour in self.values:
            for role_id in role_ids.get(str(interaction.guild.id), {}).get("결계", {}).get(hour, []):
                role = interaction.guild.get_role(role_id)
                if role and role not in interaction.user.roles:
                    await interaction.user.add_roles(role)
                    added.append(role.name)
        await interaction.response.send_message(f"✅ 결계 알람 등록 완료: {', '.join(added)}", ephemeral=True)

class BossSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(BossSelect())

class BossSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=f"{hour}시", value=str(hour)) for hour in [12, 18, 20, 22]
        ]
        super().__init__(placeholder="필보 시간 선택", min_values=1, max_values=4, options=options)

    async def callback(self, interaction: discord.Interaction):
        added = []
        for hour in self.values:
            for role_id in role_ids.get(str(interaction.guild.id), {}).get("필드보스", {}).get(hour, []):
                role = interaction.guild.get_role(role_id)
                if role and role not in interaction.user.roles:
                    await interaction.user.add_roles(role)
                    added.append(role.name)
        await interaction.response.send_message(f"✅ 필보 알람 등록 완료: {', '.join(added)}", ephemeral=True)

@bot.tree.command(name="알람초기화", description="(관리자) 서버에 필요한 알람 역할을 생성합니다.", guild=command_guild)
async def alarm_initialize(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ 관리자만 가능합니다.", ephemeral=True)
        return

    await setup_alarm_roles(interaction.guild)
    await interaction.response.send_message("✅ 알람 역할이 모두 생성되었습니다!", ephemeral=True)

@bot.tree.command(name="알람설정", description="결계/필보 알람을 설정합니다.", guild=command_guild)
async def alarm_setting(interaction: discord.Interaction):
    view = AlarmSelectView()
    await interaction.response.send_message("🔔 원하는 알람 종류를 선택하세요.", view=view, ephemeral=True)

@tasks.loop(minutes=1)
async def alarm_scheduler():
    now = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
    current_hour = now.hour
    current_minute = now.minute

    if current_minute == 57:
        for guild in bot.guilds:
            alarm_channel_id = alarm_config.get(str(guild.id))
            if not alarm_channel_id:
                continue
            channel = guild.get_channel(alarm_channel_id)
            if not channel:
                continue

            next_hour = current_hour + 1
            for category in ["결계", "필드보스"]:
                mentions = []
                for role_id in role_ids.get(str(guild.id), {}).get(category, {}).get(str(next_hour), []):
                    role = guild.get_role(role_id)
                    if role:
                        mentions.append(role.mention)
                if mentions:
                    await channel.send(f"🔔 **[{category}]** 3분 후 {next_hour}시 예정입니다!\n{' '.join(mentions)}", delete_after=180)

# FastAPI 서버
app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Bot is alive!"}

# 14분마다 서버를 깨우는 핑 함수
def keep_alive_ping():
    while True:
        try:
            url = os.environ.get("RENDER_EXTERNAL_URL")  # Render 환경변수로 서버 URL을 받을 수 있어
            if url:
                requests.get(url)
                print(f"[KeepAlive] Ping sent to {url}")
        except Exception as e:
            print(f"[KeepAlive] Ping failed: {e}")
        time.sleep(60 * 14)  # 14분 대기
        
# 디스코드 봇 실행 함수
def run_discord_bot():    
    if "dev" in sys.argv:
        bot.run(TOKEN)
    else:
        bot.run(os.environ[TOKEN])

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')

    try:
        if "dev" in sys.argv:
            # 개발 모드: 특정 서버(GUILD_ID)에만 등록
            synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
            print(f"✅ Dev 모드: {len(synced)}개 명령어를 GUILD_ID({GUILD_ID})에 등록 완료")
        else:
            # 운영 모드: 글로벌 등록
            synced = await bot.tree.sync()
            print(f"✅ Prod 모드: {len(synced)}개 명령어를 글로벌 등록 완료")
    except Exception as e:
        print(f"❌ 명령어 동기화 실패: {e}")

    await asyncio.sleep(5)
    alarm_scheduler.start()

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

@bot.tree.command(name="도움말", description="도움말을 보여줍니다", guild=command_guild)
async def help_cmd1(interaction: discord.Interaction):
    await help_command(interaction)

# 명령어 2: /명령어모음
@bot.tree.command(name="명령어모음", description="명령어 리스트를 보여줍니다", guild=command_guild)
async def help_cmd2(interaction: discord.Interaction):
    await help_command(interaction)

# 3. /물물교환 명령어 정의
@bot.tree.command(name="물물교환", description="물물교환 가능한 아이템을 검색합니다", guild=command_guild)
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
@bot.tree.command(name="채집", description="채집할 재료를 선택하세요", guild=command_guild)
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
@bot.tree.command(name="제작재료", description="제작할 재료를 선택하세요", guild=command_guild)
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
@bot.tree.command(name="알람시간표", description="필드보스 및 결계 알람 시간을 보여줍니다", guild=command_guild)
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



# 서버 실행
if __name__ == "__main__":
    threading.Thread(target=keep_alive_ping).start()
    threading.Thread(target=run_discord_bot).start()
    port = int(os.environ.get("PORT", 10000))  # Render가 제공하는 포트 사용
    uvicorn.run(app, host="0.0.0.0", port=port)