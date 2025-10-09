import os
import logging
import urllib.request
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ContextTypes, filters, ConversationHandler
)
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
from colorthief import ColorThief
import tempfile

# ======================
# 🔑 CONFIGURATION
# ======================
BOT_TOKEN = "6818501149:AAFG8g-HGVOfgD_N38NF3xWbb4v4PcyQyKY"  # ← REPLACE THIS
ADMIN_USER_IDS = {7099729191}  # ← REPLACE WITH YOUR TELEGRAM USER ID

TEMPLATE_PATH = "template.png"
BOLD_FONT_PATH = "BebasNeue-Regular.ttf"
BOLD_FONT_URL = "https://github.com/google/fonts/raw/main/ofl/bebasneue/BebasNeue-Regular.ttf"

LANGUAGE_INPUT = 1

# ======================
# 🖼️ FONT & ASSET SETUP
# ======================

def download_font_if_missing():
    if not os.path.exists(BOLD_FONT_PATH):
        try:
            print("📥 Downloading bold font (Bebas Neue)...")
            urllib.request.urlretrieve(BOLD_FONT_URL, BOLD_FONT_PATH)
            print("✅ Font downloaded successfully.")
        except Exception as e:
            logging.error(f"❌ Failed to download font: {e}")

# ======================
# 🌐 ANILIST + IMAGE UTILS
# ======================

def get_anime_data(title: str):
    query = '''
    query ($search: String) {
      Media(search: $search, type: ANIME) {
        id
        title { english native }
        studios { nodes { name } }
        genres
        coverImage { extraLarge }
        countryOfOrigin
      }
    }
    '''
    try:
        r = requests.post('https://graphql.anilist.co', json={'query': query, 'variables': {'search': title}}, timeout=10)
        data = r.json()
        if 'errors' in data or not data.get('data', {}).get('Media'):
            return None
        return data['data']['Media']
    except Exception as e:
        logging.error(f"AniList error: {e}")
        return None

def get_dominant_color(image_url: str):
    try:
        response = requests.get(image_url, timeout=10)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            tmp.write(response.content)
            tmp_path = tmp.name
        color_thief = ColorThief(tmp_path)
        dominant = color_thief.get_color(quality=1)
        os.unlink(tmp_path)
        return dominant
    except:
        return (30, 30, 50)  # fallback dark blue

def generate_thumbnail(anime_data, language_text: str = ""):
    # Load base template (your PNG with logo + banner)
    if os.path.exists(TEMPLATE_PATH):
        base = Image.open(TEMPLATE_PATH).convert("RGBA")
    else:
        base = Image.new("RGBA", (1280, 720), (255, 255, 255, 255))

    # Get poster URL
    poster_url = anime_data['coverImage']['extraLarge']

    # Extract dominant color for info box background
    dominant = get_dominant_color(poster_url)
    r, g, b = dominant
    bg_color = (min(255, r + 40), min(255, g + 40), min(255, b + 40))
    luminance = 0.299 * r + 0.587 * g + 0.114 * b
    text_color = (255, 255, 255) if luminance < 160 else (20, 20, 40)

    # Create semi-transparent overlay for info box (left side only)
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw_overlay = ImageDraw.Draw(overlay)
    # Info box area: from top to bottom, width ~750px
    draw_overlay.rectangle([(0, 0), (750, 720)], fill=bg_color + (220,))
    base = Image.alpha_composite(base, overlay)

    # Load fonts
    download_font_if_missing()
    try:
        title_font = ImageFont.truetype(BOLD_FONT_PATH, 64)
        info_font = ImageFont.load_default().font_variant(size=28)
        small_font = ImageFont.load_default().font_variant(size=24)
    except:
        title_font = ImageFont.load_default()
        info_font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    draw = ImageDraw.Draw(base)

    # Title
    title = anime_data['title']['english'] or anime_data['title']['native'] or "Unknown Title"
    draw.text((60, 80), title, fill=text_color, font=title_font)

    # Studio (only first)
    studios = anime_data['studios']['nodes'] if anime_data['studios']['nodes'] else []
    studio_name = studios[0]['name'] if studios else "Unknown Studio"
    draw.text((60, 180), f"Studio: {studio_name}", fill=text_color, font=info_font)

    # Genres
    genres = ", ".join(anime_data['genres'][:4]) if anime_data['genres'] else "N/A"
    draw.text((60, 220), f"Genres: {genres}", fill=text_color, font=small_font)

    # Language
    if language_text.strip():
        draw.text((60, 260), f"Language: {language_text}", fill=text_color, font=small_font)

    # Small Poster (below text, resized to 300x400)
    poster_img = Image.open(BytesIO(requests.get(poster_url).content)).convert("RGBA")
    poster_img = poster_img.resize((300, 400), Image.Resampling.LANCZOS)
    poster_x = 60  # Left-aligned under text
    poster_y = 320  # Below language line
    base.paste(poster_img, (poster_x, poster_y), poster_img)

    # Final output: RGB (Telegram doesn't support RGBA PNG well)
    final = Image.alpha_composite(Image.new("RGBA", base.size, (255, 255, 255)), base).convert("RGB")
    return final

# ======================
# 🤖 TELEGRAM HANDLERS
# ======================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_USER_IDS:
        await update.message.reply_text("❌ You are not authorized to use this bot.")
        return
    await update.message.reply_text(
        "🎬 Welcome!\n"
        "Use /anime <title> to generate a custom thumbnail.\n"
        "Example: /anime Jujutsu Kaisen"
    )

async def anime_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_USER_IDS:
        await update.message.reply_text("❌ You are not authorized.")
        return

    if not context.args:
        await update.message.reply_text("UsageId: /anime <anime title>")
        return

    title = " ".join(context.args)
    await update.message.reply_text("🔍 Searching AniList...")
    anime = get_anime_data(title)
    if not anime:
        await update.message.reply_text("❌ Anime not found. Try a different title.")
        return

    context.user_data['anime'] = anime
    await update.message.reply_text(
        f"✅ Found: *{anime['title']['english'] or anime['title']['native']}*\n"
        "🗣️ Please reply with language info (e.g., `Japanese`, `English Sub`, `English+Japanese`) or send /skip",
        parse_mode="Markdown"
    )
    return LANGUAGE_INPUT

async def language_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_USER_IDS:
        return

    lang_text = update.message.text
    if lang_text == "/skip":
        lang_text = ""
    anime = context.user_data.get('anime')
    if not anime:
        await update.message.reply_text("Session expired. Use /anime again.")
        return

    await update.message.reply_text("🖼️ Generating thumbnail... (this may take 5-10 seconds)")
    try:
        img = generate_thumbnail(anime, lang_text)
        bio = BytesIO()
        img.save(bio, format="JPEG", quality=95)
        bio.seek(0)
        await update.message.reply_photo(photo=bio)
    except Exception as e:
        logging.exception("Thumbnail generation failed")
        await update.message.reply_text("❌ Failed to generate thumbnail. Try again later.")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operation cancelled.")
    return ConversationHandler.END

# ======================
# 🚀 MAIN
# ======================

def main():
    logging.basicConfig(level=logging.INFO)
    download_font_if_missing()  # Ensure font is ready

    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("anime", anime_command)],
        states={
            LANGUAGE_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, language_input),
                CommandHandler("skip", lambda u, c: language_input(u, c))  # treat /skip as input
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)

    print("🚀 Anime Thumbnail Bot is running!")
    print("✅ Make sure 'template.png' is in this folder.")
    app.run_polling()

if __name__ == "__main__":
    main()
