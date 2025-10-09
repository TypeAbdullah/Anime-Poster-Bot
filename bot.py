import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from io import BytesIO
import textwrap

# Bot Token - Replace with your token from @BotFather
BOT_TOKEN = "6818501149:AAFG8g-HGVOfgD_N38NF3xWbb4v4PcyQyKY"

# AniList API endpoint
ANILIST_API = "https://graphql.anilist.co"

class AnimePosterGenerator:
    def __init__(self):
        self.width = 1280
        self.height = 720
        
    def search_anime(self, query):
        """Search anime using AniList API"""
        graphql_query = """
        query ($search: String) {
          Media(search: $search, type: ANIME) {
            id
            title {
              romaji
              english
            }
            coverImage {
              extraLarge
              large
            }
            bannerImage
            genres
            format
            episodes
            averageScore
            studios {
              nodes {
                name
              }
            }
          }
        }
        """
        
        variables = {"search": query}
        response = requests.post(
            ANILIST_API,
            json={"query": graphql_query, "variables": variables}
        )
        
        if response.status_code == 200:
            return response.json()["data"]["Media"]
        return None
    
    def download_image(self, url):
        """Download image from URL"""
        response = requests.get(url)
        return Image.open(BytesIO(response.content))
    
    def create_gradient_background(self):
        """Create vibrant gradient background"""
        img = Image.new('RGB', (self.width, self.height))
        draw = ImageDraw.Draw(img)
        
        # Create deep blue to purple gradient
        for y in range(self.height):
            r = int(20 + (80 * y / self.height))
            g = int(10 + (40 * y / self.height))
            b = int(80 + (120 * y / self.height))
            draw.line([(0, y), (self.width, y)], fill=(r, g, b))
        
        return img
    
    def add_fireworks_effect(self, img):
        """Add colorful burst effects"""
        overlay = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        # Create multiple colorful bursts
        import random
        colors = [
            (255, 100, 200, 150),  # Pink
            (100, 200, 255, 150),  # Cyan
            (255, 200, 100, 150),  # Orange
            (200, 100, 255, 150),  # Purple
            (100, 255, 200, 150),  # Mint
        ]
        
        for _ in range(15):
            x = random.randint(self.width//2, self.width - 100)
            y = random.randint(50, self.height//2)
            color = random.choice(colors)
            size = random.randint(40, 100)
            
            # Draw starburst lines
            for angle in range(0, 360, 15):
                import math
                end_x = x + int(size * math.cos(math.radians(angle)))
                end_y = y + int(size * math.sin(math.radians(angle)))
                draw.line([(x, y), (end_x, end_y)], fill=color, width=2)
        
        return Image.alpha_composite(img.convert('RGBA'), overlay)
    
    def generate_poster(self, anime_data):
        """Generate anime poster"""
        # Create base
        base = self.create_gradient_background()
        
        # Add effects
        poster = self.add_fireworks_effect(base)
        poster = poster.convert('RGB')
        
        # Add anime cover on the right
        if anime_data.get('coverImage', {}).get('extraLarge'):
            cover = self.download_image(anime_data['coverImage']['extraLarge'])
            cover = cover.resize((400, 566), Image.Resampling.LANCZOS)
            
            # Add glow effect
            mask = Image.new('L', cover.size, 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.rectangle([0, 0, cover.width, cover.height], fill=255)
            
            poster.paste(cover, (self.width - 450, (self.height - 566)//2), cover if cover.mode == 'RGBA' else None)
        
        # Add text overlay
        draw = ImageDraw.Draw(poster)
        
        # Get title
        title = anime_data['title'].get('english') or anime_data['title']['romaji']
        
        # Try to load fonts, fallback to default
        try:
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 70)
            info_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 30)
            small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        except:
            title_font = ImageFont.load_default()
            info_font = ImageFont.load_default()
            small_font = ImageFont.load_default()
        
        # Add Mayhem logo/text at top
        draw.text((30, 20), "ANIME MAYHEM", font=info_font, fill=(255, 255, 255))
        
        # Add title (wrapped)
        y_pos = 150
        wrapped_title = textwrap.wrap(title, width=25)
        for line in wrapped_title[:2]:  # Max 2 lines
            draw.text((50, y_pos), line, font=title_font, fill=(255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0))
            y_pos += 80
        
        # Add studio info
        studio = anime_data.get('studios', {}).get('nodes', [{}])[0].get('name', 'Studio Lings')
        draw.text((50, y_pos + 30), f"🎬 {studio}", font=small_font, fill=(255, 255, 255))
        
        # Add genres
        genres = ', '.join(anime_data.get('genres', [])[:4])
        draw.text((50, y_pos + 70), f"🎭 {genres}", font=small_font, fill=(255, 255, 255))
        
        # Add language/format info
        format_text = anime_data.get('format', 'TV')
        episodes = anime_data.get('episodes', '?')
        draw.text((50, y_pos + 110), f"🎙️ Japanese [Eng Sub] • {episodes} Episodes", font=small_font, fill=(255, 255, 255))
        
        # Add score if available
        if anime_data.get('averageScore'):
            draw.text((50, y_pos + 150), f"⭐ Score: {anime_data['averageScore']}/100", font=small_font, fill=(255, 255, 255))
        
        # Add sidebar text
        sidebar_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 35) if os.path.exists("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf") else title_font
        
        # Rotate text for sidebar
        sidebar = Image.new('RGBA', (500, 100), (0, 0, 0, 0))
        sidebar_draw = ImageDraw.Draw(sidebar)
        sidebar_draw.text((10, 10), "ANIME MAYHEM", font=sidebar_font, fill=(255, 255, 255))
        sidebar = sidebar.rotate(90, expand=True)
        
        poster.paste(sidebar, (self.width - 70, self.height//2 - 100), sidebar)
        
        return poster

# Bot handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    welcome_text = """
🎬 Welcome to Anime Mayhem Bot! 🎬

I can create stunning anime posters for you!

📝 How to use:
Just send me an anime name and I'll generate a beautiful poster for it.

Example: "Demon Slayer"

Let's create some amazing posters! 🎨
    """
    await update.message.reply_text(welcome_text)

async def handle_anime_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle anime search and poster generation"""
    query = update.message.text
    
    # Send processing message
    processing_msg = await update.message.reply_text("🔍 Searching for anime and generating poster...")
    
    try:
        # Search anime
        generator = AnimePosterGenerator()
        anime_data = generator.search_anime(query)
        
        if not anime_data:
            await processing_msg.edit_text("❌ Anime not found. Please try another name.")
            return
        
        # Update status
        await processing_msg.edit_text("🎨 Creating your poster...")
        
        # Generate poster
        poster = generator.generate_poster(anime_data)
        
        # Save to buffer
        buffer = BytesIO()
        poster.save(buffer, format='PNG', quality=95)
        buffer.seek(0)
        
        # Send poster
        title = anime_data['title'].get('english') or anime_data['title']['romaji']
        caption = f"🎬 {title}\n\nGenerated by Anime Mayhem Bot"
        
        await update.message.reply_photo(
            photo=buffer,
            caption=caption
        )
        
        # Delete processing message
        await processing_msg.delete()
        
    except Exception as e:
        await processing_msg.edit_text(f"❌ Error generating poster: {str(e)}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command handler"""
    help_text = """
🎬 Anime Mayhem Bot Help

Commands:
/start - Start the bot
/help - Show this help message

Usage:
Simply send any anime name to generate a poster!

Examples:
• Demon Slayer
• Attack on Titan
• Jujutsu Kaisen
• One Piece

The bot will search AniList and create a custom poster for you! 🎨
    """
    await update.message.reply_text(help_text)

def main():
    """Start the bot"""
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_anime_search))
    
    # Start bot
    print("🤖 Anime Mayhem Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
