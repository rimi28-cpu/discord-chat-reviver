import discord
from discord.ext import commands, tasks
import os
import random
import json
import asyncio
from keep_alive import keep_alive

# Start web server for keeping repl alive
keep_alive()

# Bot setup with commands
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Bot configuration
class BotConfig:
    def __init__(self):
        # REPLACE THESE WITH ACTUAL CHANNEL IDs
        self.monitored_channels = [123456789, 987654321]  
        self.inactive_threshold = 3600  # 1 hour in seconds
        self.last_activity = {}
        self.questions = []
        self.icebreakers = []
        self.load_questions()
        
    def load_questions(self):
        try:
            with open('questions.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.questions = data.get('questions', [])
                self.icebreakers = data.get('icebreakers', [])
                print(f"✅ Loaded {len(self.questions)} questions and {len(self.icebreakers)} icebreakers")
        except Exception as e:
            print(f"❌ Error loading questions: {e}")
            self.questions = ["What's on your mind today?"]
            self.icebreakers = ["How's everyone doing?"]

config = BotConfig()

# Beautiful formatting elements
EMOJI_SETS = {
    "fun": ["🎉", "✨", "🌟", "💫", "🔥", "💥", "🎊", "🎈", "🥳", "😄"],
    "nature": ["🌿", "🌸", "🍃", "🌺", "🌼", "💮", "🏵️", "🌻"],
    "food": ["🍕", "🍔", "🌮", "🍣", "🍦", "🍩", "☕", "🎂"],
    "travel": ["✈️", "🌎", "🗺️", "🧭", "🏝️", "🏔️", "🌋", "🏕️"],
    "creative": ["🎨", "🎭", "🎪", "🎯", "🎮", "🎲", "🧩", "🎪"]
}

MESSAGE_STYLES = [
    "**{emoji} CHAT REVIVER {emoji}**\n\n@everyone\n\n**Question of the Hour:** {question}\n\n*Let's get this conversation flowing!* {sparkle}",
    "**{emoji} ATTENTION AWESOME PEOPLE {emoji}**\n\n@everyone\n\n**Brain Teaser:** {question}\n\n*Share your thoughts below!* {sparkle}",
    "**{emoji} CONVERSATION STARTER {emoji}**\n\n@everyone\n\n**Let's Discuss:** {question}\n\n*Jump in and chat!* {sparkle}",
    "**{emoji} COMMUNITY CHECK-IN {emoji}**\n\n@everyone\n\n**Quick Question:** {question}\n\n*What's on your mind?* {sparkle}",
    "**{emoji} TIME TO CHAT! {emoji}**\n\n@everyone\n\n**Discussion Topic:** {question}\n\n*Let's hear from everyone!* {sparkle}"
]

def create_beautiful_message(question):
    """Create a beautifully formatted message with random emojis and styling"""
    style = random.choice(MESSAGE_STYLES)
    emoji_set = random.choice(list(EMOJI_SETS.values()))
    main_emoji = random.choice(emoji_set)
    sparkle_emoji = random.choice(["✨", "🌟", "💫", "⭐", "🔮"])
    
    return style.format(
        emoji=main_emoji,
        question=question,
        sparkle=sparkle_emoji
    )

@bot.event
async def on_ready():
    print(f'✅ {bot.user} is online!')
    print(f'📊 Monitoring {len(config.monitored_channels)} channels')
    print(f'💭 Loaded {len(config.questions)} questions and {len(config.icebreakers)} icebreakers')
    
    # Initialize last activity times
    for channel_id in config.monitored_channels:
        channel = bot.get_channel(channel_id)
        if channel:
            try:
                async for message in channel.history(limit=1):
                    config.last_activity[channel_id] = message.created_at.timestamp()
                    break
            except:
                config.last_activity[channel_id] = discord.utils.utcnow().timestamp()
    
    print("✅ Bot setup complete!")
    inactivity_check.start()

@bot.event
async def on_message(message):
    if message.author.bot:
        return
        
    if message.channel.id in config.monitored_channels:
        config.last_activity[message.channel.id] = discord.utils.utcnow().timestamp()
    
    # Process commands
    await bot.process_commands(message)

@tasks.loop(minutes=5)
async def inactivity_check():
    current_time = discord.utils.utcnow().timestamp()
    
    for channel_id in config.monitored_channels:
        last_active = config.last_activity.get(channel_id, 0)
        time_since_activity = current_time - last_active
        
        if time_since_activity >= config.inactive_threshold:
            print(f"🔔 Channel {channel_id} inactive for {time_since_activity/60:.1f} minutes - reviving!")
            await revive_channel(channel_id)
            # Reset after reviving
            config.last_activity[channel_id] = current_time

async def revive_channel(channel_id):
    channel = bot.get_channel(channel_id)
    if not channel:
        return

    # Choose between regular questions and icebreakers
    if random.random() < 0.3:  # 30% chance for icebreaker
        question = random.choice(config.icebreakers)
    else:
        question = random.choice(config.questions)
    
    beautiful_message = create_beautiful_message(question)
    
    try:
        await channel.send(beautiful_message)
        print(f"📢 Sent beautiful revival message in #{channel.name}")
    except Exception as e:
        print(f"❌ Error sending message in #{channel.name}: {e}")

# Command: !pingrandom
@bot.command(name='pingrandom')
@commands.has_permissions(administrator=True)
async def ping_random(ctx, num_users: int = 3):
    """Ping random users in the server with a fun question"""
    if num_users < 1 or num_users > 10:
        await ctx.send("❌ Please choose between 1-10 users to ping!")
        return
    
    # Get non-bot members who are online
    members = [member for member in ctx.guild.members 
               if not member.bot and member.status != discord.Status.offline]
    
    if len(members) < num_users:
        await ctx.send(f"❌ Not enough active members! Only {len(members)} available.")
        return
    
    # Select random members
    random_members = random.sample(members, num_users)
    mentions = ' '.join([member.mention for member in random_members])
    
    # Choose a random question
    question = random.choice(config.questions + config.icebreakers)
    
    # Create embed for beautiful display
    embed = discord.Embed(
        title="🎯 Random Ping Time!",
        description=f"{mentions}\n\n**{question}**",
        color=discord.Color.gold()
    )
    embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
    
    await ctx.send(embed=embed)

# Command: !chatstatus
@bot.command(name='chatstatus')
async def chat_status(ctx):
    """Check how long since last activity in monitored channels"""
    if ctx.channel.id not in config.monitored_channels:
        await ctx.send("ℹ️ This channel is not being monitored for activity.")
        return
    
    last_active = config.last_activity.get(ctx.channel.id, 0)
    if last_active == 0:
        await ctx.send("📊 No activity recorded yet for this channel.")
        return
    
    current_time = discord.utils.utcnow().timestamp()
    time_since_activity = current_time - last_active
    minutes = time_since_activity / 60
    
    if minutes < 5:
        status = "🔥 Very Active"
        color = discord.Color.green()
    elif minutes < 30:
        status = "💬 Active"
        color = discord.Color.blue()
    elif minutes < 60:
        status = "😴 Getting Quiet"
        color = discord.Color.orange()
    else:
        status = "💀 Inactive"
        color = discord.Color.red()
    
    embed = discord.Embed(
        title="📊 Channel Activity Status",
        description=f"**Status:** {status}\n**Last message:** {minutes:.1f} minutes ago",
        color=color
    )
    await ctx.send(embed=embed)

# Command: !reloadquestions
@bot.command(name='reloadquestions')
@commands.has_permissions(administrator=True)
async def reload_questions(ctx):
    """Reload questions from the JSON file"""
    config.load_questions()
    await ctx.send(f"✅ Reloaded {len(config.questions)} questions and {len(config.icebreakers)} icebreakers!")

# Error handling
@ping_random.error
async def ping_random_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You need administrator permissions to use this command!")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("❌ Please provide a valid number! Usage: `!pingrandom 3`")

print("🤖 Starting Discord Chat Reviver Bot...")
bot.run(os.getenv('DISCORD_TOKEN'))
