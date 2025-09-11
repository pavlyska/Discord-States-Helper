import discord
from discord import app_commands
import json
import os

# === НАСТРОЙКИ ===
BOT_TOKEN = ""
OWNER_ID = 
GUILD_ID =   # ← Убедись, что правильный

# === ФАЙЛ ДЛЯ ХРАНЕНИЯ ТЕМ ПОМОЩИ ===
THEMES_FILE = "help_themes.json"

if not os.path.exists(THEMES_FILE):
    with open(THEMES_FILE, 'w', encoding='utf-8') as f:
        json.dump({}, f, ensure_ascii=False, indent=4)

# === БОТ ===
intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# === ЗАГРУЗКА/СОХРАНЕНИЕ ТЕМ ===
def load_themes():
    with open(THEMES_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_theme(name: str, title: str, description: str, color: int = 0x00ff88, image: str = None):
    themes = load_themes()
    themes[name] = {
        "title": title,
        "description": description,
        "color": color,
        "image": image
    }
    with open(THEMES_FILE, 'w', encoding='utf-8') as f:
        json.dump(themes, f, ensure_ascii=False, indent=4)

def delete_theme(name: str) -> bool:
    themes = load_themes()
    if name in themes:
        del themes[name]
        with open(THEMES_FILE, 'w', encoding='utf-8') as f:
            json.dump(themes, f, ensure_ascii=False, indent=4)
        return True
    return False

# === ПРОВЕРКА: ТОЛЬКО ДЛЯ ВЛАДЕЛЬЦА ===
def is_owner(interaction: discord.Interaction) -> bool:
    return interaction.user.id == OWNER_ID


# === МОДАЛЬНОЕ ОКНО ДЛЯ ДОБАВЛЕНИЯ ТЕМЫ ===
class AddThemeModal(discord.ui.Modal, title="📘 Добавить тему помощи"):
    theme_key = discord.ui.TextInput(
        label="🔑 Ключ темы",
        placeholder="например: модерация",
        min_length=2,
        max_length=32
    )
    theme_title = discord.ui.TextInput(
        label="🏷 Заголовок",
        placeholder="Модерация сервера",
        min_length=1,
        max_length=100
    )
    theme_content = discord.ui.TextInput(
        label="📝 Описание",
        style=discord.TextStyle.long,
        placeholder="Объясни, как использовать...",
        min_length=1,
        max_length=2000
    )
    theme_image = discord.ui.TextInput(
        label="🖼 Ссылка на изображение",
        required=False,
        placeholder="https://i.imgur.com/..."
    )

    async def on_submit(self, interaction: discord.Interaction):
        key = self.theme_key.value.strip().lower()
        if ' ' in key:
            return await interaction.response.send_message(
                "❌ **Ключ не должен содержать пробелов.** Используй `подчёркивание_иликириллица`.", 
                ephemeral=True
            )

        save_theme(
            name=key,
            title=self.theme_title.value.strip(),
            description=self.theme_content.value.strip(),
            image=self.theme_image.value.strip() if self.theme_image.value else None
        )

        await interaction.response.send_message(
            f"✅ **Тема `{key}` успешно добавлена!** Теперь её можно выбрать в `/dhelp`.",
            ephemeral=True
        )
        await sync_commands()  # Обновляем меню


# === VIEW С ЗАЩИТОЙ И МЕНЮ ===
class HelpView(discord.ui.View):
    def __init__(self, user: discord.User):
        super().__init__(timeout=300)  # 5 минут
        self.user = user  # Только этот пользователь может выбрать

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "<:stop:1405108141854818394> **Это не твоё меню.** Используй `/dhelp`, чтобы открыть своё.",
                ephemeral=True
            )
            return False
        return True

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        # Можно обновить сообщение, если нужно


# === КОМАНДА /dhelp — ПОКАЗЫВАЕТ МЕНЮ ===
@tree.command(name="dhelp", description="📘 Показать интерактивное меню помощи", guild=discord.Object(id=GUILD_ID))
async def dhelp_command(interaction: discord.Interaction):
    themes = load_themes()
    if not themes:
        embed = discord.Embed(
            title="<:rules:1397539471989280808> Помощь",
            description="<:earh:1405761727920082994> Пока нет доступных тем. Администратор может добавить их через `/add`.",
            color=0x666666
        )
        embed.set_footer(text="Создано с ❤️")
        return await interaction.response.send_message(embed=embed)

    # Создаём меню
    options = [
        discord.SelectOption(
            label=key,
            description=theme["title"][:50],
            emoji="<:rules:1397539471989280808>"
        ) for key, theme in themes.items()
    ]

    select = discord.ui.Select(
        placeholder="🔍 Выбери интересующую тему...",
        options=options
    )

    async def callback(select_interaction: discord.Interaction):
        selected_key = select.values[0]
        theme = themes.get(selected_key)
        if not theme:
            return await select_interaction.response.send_message("❌ Тема не найдена.", ephemeral=True)

        embed = discord.Embed(
            title=f"<:rules:1397539471989280808> {theme['title']}",
            description=theme['description'],
            color=theme.get("color", 0x00ff88)
        )
        if theme.get("image"):
            embed.set_image(url=theme["image"])
        embed.set_footer(text=f"Тема: {selected_key} | Запросил: {select_interaction.user.display_name}")

        await select_interaction.response.send_message(embed=embed)

    select.callback = callback

    # Добавляем меню в view
    view = HelpView(user=interaction.user)
    view.add_item(select)

    embed = discord.Embed(
        title="<:rules:1397539471989280808> Добро пожаловать в систему помощи!",
        description="Выбери тему ниже, чтобы получить подробную информацию.",
        color=0x00ff88
    )
    embed.add_field(
        name="<:earh:1405761727920082994> Доступные темы",
        value=f"Всего: **{len(themes)}**\n" + "\n".join([f"• `{k}` → {t['title']}" for k, t in list(themes.items())[:5]]),
        inline=False
    )
    if len(themes) > 5:
        embed.add_field(name="...", value=f"и ещё {len(themes) - 5}...", inline=False)

    await interaction.response.send_message(embed=embed, view=view)


# === КОМАНДА /add — ДОБАВИТЬ ТЕМУ (ТОЛЬКО ДЛЯ МЕНЯ) ===
@tree.command(name="add", description="Добавить тему в /dhelp", guild=discord.Object(id=GUILD_ID))
@app_commands.check(is_owner)
async def add_theme(interaction: discord.Interaction):
    modal = AddThemeModal()
    await interaction.response.send_modal(modal)


# === КОМАНДА /remove — УДАЛИТЬ ТЕМУ (ТОЛЬКО ДЛЯ МЕНЯ) ===
@tree.command(name="remove", description="Удалить тему из /dhelp", guild=discord.Object(id=GUILD_ID))
@app_commands.check(is_owner)
async def remove_theme(interaction: discord.Interaction, theme: str):
    theme = theme.lower().strip()
    if delete_theme(theme):
        await interaction.response.send_message(
            embed=discord.Embed(
                title="🗑 Тема удалена",
                description=f"✅ Тема `{theme}` успешно удалена.",
                color=0xff3366
            )
        )
        await sync_commands()  # Обновляем
    else:
        await interaction.response.send_message(
            embed=discord.Embed(
                title="❌ Ошибка",
                description=f"Тема `{theme}` не найдена.",
                color=0xff0000
            )
        )


# === СИНХРОНИЗАЦИЯ КОММАНД ===
async def sync_commands():
    guild = discord.Object(id=GUILD_ID)
    tree.clear_commands(guild=guild)

    # Перерегистрируем
    tree.add_command(dhelp_command, guild=guild)
    tree.add_command(add_theme, guild=guild)
    tree.add_command(remove_theme, guild=guild)

    # Только владелец может использовать /add и /remove
    for cmd in tree.get_commands(guild=guild):
        if cmd.name in ("add", "remove"):
            cmd.checks = [is_owner]

    await tree.sync(guild=guild)


# === ОБРАБОТЧИК ОШИБОК ===
@tree.error
async def on_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message(
            embed=discord.Embed(
                title="🔒 Доступ запрещён",
                description="Эта команда доступна только владельцу бота.",
                color=0xff0000
            ),
            ephemeral=True
        )
    else:
        print(f"[ОШИБКА] {error}")


# === ЗАПУСК ===
@client.event
async def on_ready():
    print(f"✅ Бот запущен как {client.user}")
    await client.wait_until_ready()

    guild = client.get_guild(GUILD_ID)
    if not guild:
        print(f"❌ Бот не состоит на сервере с ID {GUILD_ID}")
        return

    await sync_commands()
    print("🔧 Команды (/dhelp, /add, /remove) синхронизированы.")

    activity = discord.CustomActivity(name="Да я прогибаюсь бойчик, только если занимаюсь йогой")
    await client.change_presence(activity=activity)
    print("🟢 Статус установлен.")

client.run(BOT_TOKEN)
