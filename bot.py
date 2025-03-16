import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, CallbackContext
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import yt_dlp

TELEGRAM_BOT_TOKEN = '7853516235:AAGlijiKbpiyj9nb1bHch1sbw8eYftS2pSI'
YOUTUBE_API_KEY = 'AIzaSyCwI3VFYq-_HHgbAaVcMnbMx_JHtEYnsmU'

def search_youtube(query: str) -> tuple[str, str]:
    """Search YouTube for a video and return URL and title."""
    try:
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
        request = youtube.search().list(
            q=query,
            part='snippet',
            type='video',
            maxResults=1
        )
        response = request.execute()
        
        if not response.get('items'):
            return None, "No results found"
            
        video_id = response['items'][0]['id']['videoId']
        video_title = response['items'][0]['snippet']['title']
        return f"https://www.youtube.com/watch?v={video_id}", video_title
        
    except HttpError as e:
        print(f"YouTube API Error: {e}")
        return None, "Error searching YouTube"
    except Exception as e:
        print(f"Search Error: {e}")
        return None, "Search failed"

async def download_audio(url: str) -> bool:
    """Download audio using yt-dlp in a thread."""
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': 'music.%(ext)s',
        'quiet': True,
    }
    
    try:
        loop = asyncio.get_running_loop()
        with ThreadPoolExecutor() as pool:
            await loop.run_in_executor(pool, lambda: yt_dlp.YoutubeDL(ydl_opts).download([url]))
        return True
    except Exception as e:
        print(f"Download Error: {e}")
        return False

async def play_music(update: Update, context: CallbackContext) -> None:
    """Handle music playback requests."""
    try:
        query = update.message.text.replace("پخش ", "").strip()
        
        if not query:
            await update.message.reply_text("⚠️ لطفا نام آهنگ را وارد کنید.")
            return

        await update.message.reply_text("🔎 در حال جستجوی آهنگ...")
        
        video_url, video_title = search_youtube(query)
        if not video_url:
            await update.message.reply_text("❌ آهنگ مورد نظر یافت نشد.")
            return

        await update.message.reply_text(f"🎵 در حال پخش: {video_title}\n🔗 {video_url}")
        
        # Show downloading status
        status_msg = await update.message.reply_text("⏬ در حال دانلود آهنگ...")
        
        # Download audio in background thread
        success = await download_audio(video_url)
        if not success:
            await status_msg.edit_text("❌ خطا در دانلود آهنگ")
            return

        # Send audio file
        await status_msg.edit_text("📤 در حال آپلود آهنگ...")
        try:
            await update.message.reply_audio(
                audio=open('music.mp3', 'rb'),
                title=video_title,
                performer="YouTube"
            )
        finally:
            # Cleanup file
            if os.path.exists('music.mp3'):
                os.remove('music.mp3')
                
        await status_msg.delete()

    except Exception as e:
        print(f"Error: {e}")
        await update.message.reply_text("⚠️ خطایی رخ داد. لطفا دوباره امتحان کنید.")

def main() -> None:
    """Start the bot."""
    # Create Application instance
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Add handlers
    application.add_handler(
        MessageHandler(filters.TEXT & filters.Regex(r'^پخش اهنگ'), play_music)
    )

    # Run bot with graceful shutdown
    try:
        print("🤖 Bot is running... Press Ctrl+C to stop")
        application.run_polling()
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped gracefully")
    finally:
        # Perform any cleanup here
        if os.path.exists('music.mp3'):
            os.remove('music.mp3')

if __name__ == '__main__':
    main()   