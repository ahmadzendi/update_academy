import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import os
import json

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
API_URL = "https://indodax.com/academy/wp-json/api/v1/latest-article?lang=id&category=semua&label_category="
LAST_ID_FILE = "last_id.txt"
FILTER_KEY_FILE = "filter_key.json"

def get_wib_time():
    return datetime.now(ZoneInfo("Asia/Jakarta")).strftime('%d/%m/%Y %H:%M:%S WIB')

def get_last_id():
    try:
        with open(LAST_ID_FILE, "r") as f:
            return f.read().strip()
    except:
        return None

def set_last_id(article_id):
    with open(LAST_ID_FILE, "w") as f:
        f.write(str(article_id))

def get_filter_keys():
    if os.path.exists(FILTER_KEY_FILE):
        with open(FILTER_KEY_FILE, "r") as f:
            return set(json.load(f))
    # Default filter jika file belum ada
    default = {"listing", "token"}
    set_filter_keys(default)
    return default

def set_filter_keys(keys):
    with open(FILTER_KEY_FILE, "w") as f:
        json.dump(list(keys), f)

async def key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    keys = get_filter_keys()
    if context.args:
        word = context.args[0].strip().lower()
        if word in keys:
            keys.remove(word)
            await update.message.reply_text(f"Kata kunci '{word}' dihapus dari filter.")
        else:
            keys.add(word)
            await update.message.reply_text(f"Kata kunci '{word}' ditambahkan ke filter.")
        set_filter_keys(keys)
    else:
        if keys:
            daftar = ', '.join(keys)
            await update.message.reply_text(
                f"Chat ID tujuan: `{CHAT_ID}`\n"
                f"Daftar kata kunci filter aktif: {daftar}",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                f"Chat ID tujuan: `{CHAT_ID}`\n"
                "Filter kosong. Semua artikel akan dikirim.",
                parse_mode="Markdown"
            )

async def check_new_article(context: ContextTypes.DEFAULT_TYPE):
    try:
        response = requests.get(API_URL)
        data = response.json()
        artikel = data['datas'][0]
        artikel_id = artikel.get('id')
        last_id = get_last_id()

        judul = artikel.get('post_title', 'Judul tidak ditemukan')
        link = artikel.get('permalink', 'Link tidak ditemukan')
        tanggal_sekarang = get_wib_time()
        pesan = f"""Indodax Academy News Update:

{judul}
{link}
Tanggal Update: {tanggal_sekarang}"""

        keys = get_filter_keys()

        if str(artikel_id) != str(last_id):
            if keys and not any(k in judul.lower() for k in keys):
                print(f"Artikel baru tidak mengandung kata kunci {keys}, tidak dikirim.")
            else:
                await context.bot.send_message(chat_id=CHAT_ID, text=pesan)
                print("Artikel baru dikirim ke grup/channel!")
            set_last_id(artikel_id)
        else:
            print("Belum ada artikel baru.")
    except Exception as e:
        print("Error:", e)

async def resetid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        os.remove(LAST_ID_FILE)
        await update.message.reply_text("last_id.txt sudah direset. Artikel terbaru akan dikirim lagi jika sesuai filter.")
    except Exception as e:
        await update.message.reply_text(f"Gagal reset: {e}")

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("key", key))
    app.add_handler(CommandHandler("resetid", resetid))

    # Cek artikel baru setiap 60 detik dengan JobQueue
    app.job_queue.run_repeating(check_new_article, interval=30, first=5)

    print("Bot berjalan...")
    app.run_polling()

if __name__ == "__main__":
    main()
