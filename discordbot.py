import discord
from discord.ext import commands
import yt_dlp as youtube_dl
import asyncio
import random

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

bot.song_queue = []
bot.is_looping = False
bot.volume = 0.5  # Default volume (0.0 to 1.0)

FFMPEG_PATH = "D:/ffmpeg-2025-03-31-git-35c091f4b7-essentials_build/bin/ffmpeg.exe"

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

@bot.command()
async def join(ctx):
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        await channel.connect()
        await ctx.send(f"🎧 Joined `{channel}`")
    else:
        await ctx.send("❗ Join a voice channel first!")

@bot.command()
async def play(ctx, *, url_or_name):
    if not ctx.voice_client:
        await ctx.invoke(bot.get_command("join"))

    if url_or_name.startswith("http"):
        url = url_or_name
    else:
        search_query = f"ytsearch:{url_or_name}"
        ydl_opts = {
            'quiet': True,
            'format': 'bestaudio/best',
            'noplaylist': True,
        }

        try:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(search_query, download=False)
                if 'entries' in info:
                    url = info['entries'][0]['webpage_url']
                else:
                    await ctx.send("❗ Couldn't find a video for that search!")
                    return
        except Exception as e:
            await ctx.send(f"❗ Search failed: {e}")
            return

    bot.song_queue.append(url)
    await ctx.send(f"🎶 Added to queue: {url}")

    if not ctx.voice_client.is_playing() and not ctx.voice_client.is_paused():
        await play_next(ctx)

async def play_next(ctx):
    if not bot.song_queue:
        return

    url = bot.song_queue[0]

    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
    }

    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            stream_url = info['url']
            title = info.get('title', 'Unknown')
            webpage_url = info.get('webpage_url', url)
            thumbnail = info.get('thumbnail', '')

        vc = ctx.voice_client

        def after_playing(error):
            if error:
                print(f"Error after playing: {error}")
            future = asyncio.run_coroutine_threadsafe(play_after(ctx), bot.loop)
            try:
                future.result()
            except Exception as e:
                print(f"Error in after function: {e}")

        source = discord.FFmpegPCMAudio(stream_url, executable=FFMPEG_PATH)
        vc.play(discord.PCMVolumeTransformer(source, volume=bot.volume), after=after_playing)

        embed = discord.Embed(title="Now Playing 🎶", description=f"[{title}]({webpage_url})", color=0x1DB954)
        embed.set_thumbnail(url=thumbnail)
        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"❗ Playback error: {e}")
        bot.song_queue.pop(0)
        await play_next(ctx)

async def play_after(ctx):
    if not bot.is_looping and bot.song_queue:
        bot.song_queue.pop(0)
    if bot.song_queue:
        await play_next(ctx)

@bot.command()
async def pause(ctx):
    if ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("⏸️ Paused")
    else:
        await ctx.send("❗ Nothing is playing.")

@bot.command()
async def resume(ctx):
    if ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("▶️ Resumed")
    else:
        await ctx.send("❗ Nothing is paused.")

@bot.command()
async def stop(ctx):
    if ctx.voice_client:
        ctx.voice_client.stop()
        bot.song_queue.clear()
        await ctx.send("⏹️ Stopped and cleared the queue.")

@bot.command()
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭️ Skipped")
    else:
        await ctx.send("❗ Nothing is playing.")

@bot.command()
async def loop(ctx):
    bot.is_looping = not bot.is_looping
    status = "enabled 🔁" if bot.is_looping else "disabled"
    await ctx.send(f"Loop is now {status}")

@bot.command()
async def queue(ctx):
    if bot.song_queue:
        queue_list = "\n".join([f"{i+1}. {url}" for i, url in enumerate(bot.song_queue)])
        await ctx.send(f"📜 **Current Queue:**\n{queue_list}")
    else:
        await ctx.send("🕳️ The queue is empty.")

@bot.command()
async def clear_queue(ctx):
    bot.song_queue.clear()
    await ctx.send("🧹 Queue cleared.")

@bot.command()
async def remove(ctx, index: int):
    if 0 < index <= len(bot.song_queue):
        removed = bot.song_queue.pop(index - 1)
        await ctx.send(f"❌ Removed: {removed}")
    else:
        await ctx.send("❗ Invalid index.")

@bot.command()
async def move(ctx, from_index: int, to_index: int):
    try:
        song = bot.song_queue.pop(from_index - 1)
        bot.song_queue.insert(to_index - 1, song)
        await ctx.send(f"🔀 Moved song to position {to_index}")
    except IndexError:
        await ctx.send("❗ Invalid indexes.")

@bot.command()
async def shuffle(ctx):
    random.shuffle(bot.song_queue)
    await ctx.send("🔀 Queue shuffled!")

@bot.command()
async def nowplaying(ctx):
    if not bot.song_queue:
        await ctx.send("❗ Nothing is playing.")
        return

    try:
        url = bot.song_queue[0]
        with youtube_dl.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Unknown')
            webpage_url = info.get('webpage_url', url)
            thumbnail = info.get('thumbnail', '')

        embed = discord.Embed(title="Now Playing 🎶", description=f"[{title}]({webpage_url})", color=0x00ffcc)
        embed.set_thumbnail(url=thumbnail)
        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"❗ Couldn't fetch now playing info: {e}")

@bot.command()
async def volume(ctx, vol: int):
    if 0 <= vol <= 100:
        bot.volume = vol / 100
        await ctx.send(f"🔊 Volume set to {vol}%")
    else:
        await ctx.send("❗ Please choose a value between 0 and 100.")

@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        bot.song_queue.clear()
        await ctx.send("👋 Disconnected and cleared the queue.")
    else:
        await ctx.send("❗ I'm not in a voice channel.")

# 🚨 Add your bot token here
bot.run("")
