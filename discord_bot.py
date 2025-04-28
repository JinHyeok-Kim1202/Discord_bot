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
else:
    CONFIG_FILE = "json/config/config_prod.json"

# config 불러오기
with open(CONFIG_FILE, "r", encoding="utf-8") as f:
    config_data = json.load(f)

TOKEN = config_data["TOKEN"]
GUILD_ID = config_data["GUILD_ID"]

if "dev" in sys.argv:
    command_guild = discord.Object(id=GUILD_ID)  # 개발 서버용
else:
    command_guild = None  # 글로벌 등록용

# 알람 유저 데이터
ALARM_DATA_FILE = "json/alarm/alarm_users.json"
if os.path.exists(ALARM_DATA_FILE):
    with open(ALARM_DATA_FILE, "r", encoding="utf-8") as f:
        registered_users = json.load(f)
else:
    registered_users = {"결계": [], "필드보스": []}

# 알람 채널 설정 데이터
ALARM_CONFIG_FILE = "json/alarm/alarm_config.json"
if os.path.exists(ALARM_CONFIG_FILE):
    with open(ALARM_CONFIG_FILE, "r", encoding="utf-8") as f:
        alarm_config = json.load(f)
else:
    alarm_config = {"alarm_channel_id": None}

def save_registered_users():
    with open(ALARM_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(registered_users, f, ensure_ascii=False, indent=4)

def save_alarm_config():
    with open(ALARM_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(alarm_config, f, ensure_ascii=False, indent=4)

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

# 버튼 뷰
class AlarmSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="결계 알람 설정", style=discord.ButtonStyle.primary, custom_id="barrier_setting")
    async def barrier_setting(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(view=BarrierSelectView(), ephemeral=True)

    @discord.ui.button(label="필드보스 알람 설정", style=discord.ButtonStyle.success, custom_id="boss_setting")
    async def boss_setting(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(view=BossSelectView(), ephemeral=True)

class BarrierSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(BarrierSelect())

class BossSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(BossSelect())

class BarrierSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="0시", value="0"),
            discord.SelectOption(label="3시", value="3"),
            discord.SelectOption(label="6시", value="6"),
            discord.SelectOption(label="9시", value="9"),
            discord.SelectOption(label="12시", value="12"),
            discord.SelectOption(label="15시", value="15"),
            discord.SelectOption(label="18시", value="18"),
            discord.SelectOption(label="21시", value="21"),
        ]
        super().__init__(placeholder="원하는 결계 시간을 선택하세요", min_values=1, max_values=8, options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_hours = [int(value) for value in self.values]
        added = []
        for hour in selected_hours:
            role_ids_list = registered_users["결계"].get(str(hour), [])
            for role_id in role_ids_list:
                role = interaction.guild.get_role(role_id)
                if role:
                    await interaction.user.add_roles(role)
                    added.append(role.name)
        await interaction.response.send_message(f"✅ 결계 알람 등록 완료: {', '.join(added)}", ephemeral=True)

class BossSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="12시", value="12"),
            discord.SelectOption(label="18시", value="18"),
            discord.SelectOption(label="20시", value="20"),
            discord.SelectOption(label="22시", value="22"),
        ]
        super().__init__(placeholder="원하는 필보 시간을 선택하세요", min_values=1, max_values=4, options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_hours = [int(value) for value in self.values]
        added = []
        for hour in selected_hours:
            role_ids_list = registered_users["필드보스"].get(str(hour), [])
            for role_id in role_ids_list:
                role = interaction.guild.get_role(role_id)
                if role:
                    await interaction.user.add_roles(role)
                    added.append(role.name)
        await interaction.response.send_message(f"✅ 필보 알람 등록 완료: {', '.join(added)}", ephemeral=True)


# /알람설정 명령어
@bot.tree.command(name="알람설정", description="알람을 설정할 수 있습니다", guild=command_guild)
async def alarm_setting(interaction: discord.Interaction):
    view = AlarmSelectView()
    await interaction.response.send_message("🔔 원하는 알람을 선택하세요!", view=view, ephemeral=True)
    
@bot.tree.command(name="알람채널설정", description="알람을 보낼 채널을 설정합니다 (관리자만)", guild=command_guild)
@app_commands.describe(channel="알람을 보낼 채널을 선택하세요")
async def set_alarm_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ 이 명령어는 서버 관리자만 사용할 수 있습니다.", ephemeral=True)
        return

    alarm_config["alarm_channel_id"] = channel.id
    save_alarm_config()

    if alarm_scheduler.is_running():
        await interaction.response.send_message(f"❌ 이미 설정되어있습니다.", ephemeral=True, delete_after=180)
        alarm_scheduler.cancel()
        return
    alarm_scheduler.start()

    await interaction.response.send_message(f"✅ 알람 채널이 {channel.mention}로 설정되었습니다! (알람 스케줄러 재시작 완료)", ephemeral=True, delete_after=180)


# 자동 알람 스케줄러
@tasks.loop(minutes=1)
async def alarm_scheduler():
    now = datetime.datetime.utcnow() + datetime.timedelta(hours=9)  # 한국 시간
    current_hour = now.hour
    current_minute = now.minute

    alarm_channel_id = alarm_config.get("alarm_channel_id")
    if not alarm_channel_id:
        print("❌ 알람 채널이 아직 설정되지 않았습니다.")
        return

    channel = bot.get_channel(alarm_channel_id)
    if not channel:
        print("❌ 알람 채널을 찾을 수 없습니다.")
        return

    # 결계 알람 (목표: 12, 15, 18, 21) -> 실제 울릴 시간: 11:57, 14:57, 17:57, 20:57
    barrier_times = [0, 3, 6, 9, 12, 15, 18, 21]
    if current_minute == 57 and (current_hour + 1) in barrier_times:
        role_id = registered_users["결계"][current_hour + 1]
        role = channel.guild.get_role(role_id)
        if role:
            await channel.send(f"🔔 **결계 알람**: 3분 후 {current_hour+1}시에 시작합니다! {role.mention}", delete_after=180)

    # 필드보스 알람
    if current_minute == 57 and (current_hour + 1) in [12, 18, 20, 22]:
        role_id = registered_users["필드보스"][current_hour + 1]
        role = channel.guild.get_role(role_id)
        if role:
            await channel.send(f"⚔️ **필드보스 알람**: 3분 후 {current_hour+1}시에 출현합니다! {role.mention}", delete_after=180)

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