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
            season
            seasonYear
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
    
    def create_aesthetic_background(self):
        """Create aesthetic gradient background with patterns"""
        img = Image.new('RGB', (self.width, self.height))
        draw = ImageDraw.Draw(img)
        
        # Create smooth purple to deep blue gradient
        for y in range(self.height):
            # Smooth transition from purple to deep blue
            r = int(60 - (30 * y / self.height))
            g = int(40 - (20 * y / self.height))
            b = int(120 + (60 * y / self.height))
            draw.line([(0, y), (self.width, y)], fill=(r, g, b))
        
        return img
    
    def add_fireworks_effect(self, img):
        """Add colorful firework bursts"""
        overlay = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        import random
        
        # Define firework positions and colors
        fireworks = [
            {'x': 650, 'y': 80, 'color': (255, 180, 100, 180), 'size': 80},
            {'x': 850, 'y': 120, 'color': (255, 100, 200, 180), 'size': 70},
            {'x': 750, 'y': 200, 'color': (100, 200, 255, 180), 'size': 60},
            {'x': 650, 'y': 280, 'color': (200, 100, 255, 180), 'size': 65},
            {'x': 550, 'y': 150, 'color': (100, 255, 200, 180), 'size': 55},
        ]
        
        for fw in fireworks:
            x, y = fw['x'], fw['y']
            color = fw['color']
            size = fw['size']
            
            # Draw starburst pattern
            for angle in range(0, 360, 12):
                import math
                end_x = x + int(size * math.cos(math.radians(angle)))
                end_y = y + int(size * math.sin(math.radians(angle)))
                
                # Thicker lines
                draw.line([(x, y), (end_x, end_y)], fill=color, width=3)
                
                # Add small circles at the end
                circle_size = 4
                draw.ellipse([end_x-circle_size, end_y-circle_size, 
                            end_x+circle_size, end_y+circle_size], fill=color)
        
        return Image.alpha_composite(img.convert('RGBA'), overlay)
    
    def generate_poster(self, anime_data):
        """Generate anime poster"""
        # Create base
        base = self.create_aesthetic_background()
        
        # Add effects
        poster = self.add_fireworks_effect(base)
        poster = poster.convert('RGB')
        
        # Add anime cover on the right
        if anime_data.get('coverImage', {}).get('extraLarge'):
            cover = self.download_image(anime_data['coverImage']['extraLarge'])
            # Larger cover
            cover = cover.resize((450, 636), Image.Resampling.LANCZOS)
            
            # Position cover on the right
            cover_x = self.width - 480
            cover_y = (self.height - 636) // 2
            
            poster.paste(cover, (cover_x, cover_y), cover if cover.mode == 'RGBA' else None)
        
        # Add text overlay
        draw = ImageDraw.Draw(poster)
        
        # Get title
        title = anime_data['title'].get('english') or anime_data['title']['romaji']
        
        # Try to load fonts with larger sizes
        try:
            # Much larger fonts
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 90)
            info_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 38)
            small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
            logo_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 42)
        except:
            title_font = ImageFont.load_default()
            info_font = ImageFont.load_default()
            small_font = ImageFont.load_default()
            logo_font = ImageFont.load_default()
        
        # Add ANIME MAYHEM logo at top
        draw.text((40, 30), "ANIME MAYHEM", font=logo_font, fill=(255, 255, 255), 
                 stroke_width=2, stroke_fill=(0, 0, 0))
        
        # Add title (wrapped) - much larger
        y_pos = 160
        wrapped_title = textwrap.wrap(title, width=18)
        for line in wrapped_title[:2]:  # Max 2 lines
            draw.text((50, y_pos), line, font=title_font, fill=(255, 255, 255), 
                     stroke_width=3, stroke_fill=(0, 0, 0))
            y_pos += 100
        
        # Add studio info with larger font
        studio = anime_data.get('studios', {}).get('nodes', [{}])[0].get('name', 'Unknown Studio')
        draw.text((50, y_pos + 40), f"🎬 {studio}", font=info_font, fill=(255, 255, 255))
        
        # Add genres with larger font
        genres = ', '.join(anime_data.get('genres', [])[:3])
        draw.text((50, y_pos + 95), f"🎭 {genres}", font=info_font, fill=(255, 255, 255))
        
        # Add season and episodes info
        season = anime_data.get('season', '').capitalize() if anime_data.get('season') else 'Unknown'
        year = anime_data.get('seasonYear', '')
        episodes = anime_data.get('episodes', '?')
        
        season_text = f"{season} {year}" if year else season
        episode_text = f"{episodes} Episodes" if episodes != '?' else "Episodes TBA"
        
        draw.text((50, y_pos + 150), f"📅 {season_text} • {episode_text}", 
                 font=info_font, fill=(255, 255, 255))
        
        # Add score if available
        if anime_data.get('averageScore'):
            draw.text((50, y_pos + 205), f"⭐ Score: {anime_data['averageScore']}/100", 
                     font=info_font, fill=(255, 255, 255))
        
        # Add vertical "ANIME MAYHEM" text on the right side
        # Create text image for rotation
        sidebar_text = "ANIME MAYHEM"
        
        # Calculate text size for proper positioning
        bbox = draw.textbbox((0, 0), sidebar_text, font=logo_font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Create temporary image for text
        text_img = Image.new('RGBA', (text_width + 20, text_height + 20), (0, 0, 0, 0))
        text_draw = ImageDraw.Draw(text_img)
        text_draw.text((10, 10), sidebar_text, font=logo_font, fill=(255, 255, 255), 
                      stroke_width=2, stroke_fill=(0, 0, 0))
        
        # Rotate 90 degrees
        text_img = text_img.rotate(90, expand=True)
        
        # Paste on main image
        text_x = self.width - 60
        text_y = self.height // 2 - text_img.height // 2
        poster.paste(text_img, (text_x, text_y), text_img)
        
        return poster

# Bot handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    welcome_text = """
🎬 Welcome to Anime Mayhem Bot! 🎬

I can create stunning anime posters for you!

📝 How to use:
Just send me an anime name and I'll generate a beautiful poster for it.

Example: "One Piece"

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
• One Piece
• Demon Slayer
• Attack on Titan
• Jujutsu Kaisen

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
