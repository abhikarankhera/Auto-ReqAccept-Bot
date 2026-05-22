import os
from pyrogram import Client, filters
from motor.motor_asyncio import AsyncIOMotorClient
from aiohttp import web
import asyncio

# Fetch Environment Variables
API_ID = int(os.environ.get('API_ID'))
API_HASH = os.environ.get('API_HASH')
BOT_TOKEN = os.environ.get('BOT_TOKEN')
DB_URL = os.environ.get('DB_URL')
ADMINS = int(os.environ.get('ADMINS'))

# Database Setup
Dbclient = AsyncIOMotorClient(DB_URL)
Cluster = Dbclient['Cluster0']
Data = Cluster['users']

# Initialize Telegram Bot
Bot = Client(name='AutoAcceptBot', api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ----------------- KOYEB HEALTH CHECK WEB SERVER -----------------
async def health_check(request):
    # Returns 200 OK to Koyeb so the service stays green
    return web.Response(text="Bot is running smoothly!", status=200)

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    # Koyeb routes web traffic to port 8000 by default
    site = web.TCPSite(runner, '0.0.0.0', 8000)
    await site.start()
    print("Health check web server started on port 8000")
# -----------------------------------------------------------------

@Bot.on_message(filters.command("start") & filters.private)
async def start_handler(c, m):
    user_id = m.from_user.id
    if not await Data.find_one({'id': user_id}):
        await Data.insert_one({'id': user_id})
    await m.reply_text(text=f"Hello {m.from_user.mention}! Send join requests to the channel to interact.")

@Bot.on_chat_join_request()
async def req_accept(c, m):
    user_id = m.from_user.id
    chat_id = m.chat.id
    if not await Data.find_one({'id': user_id}): 
        await Data.insert_one({'id': user_id})
    
    # ❌ Line commented out so requests stay pending!
    # await c.approve_chat_join_request(chat_id, user_id) 
    
    try: 
        # Your custom marketing/SMM promo text sent to their DMs
        await c.send_message(user_id, "Welcome! Your request is received. While you wait, check out our panel here: https://yourlink.com")
    except Exception as e: 
        print(f"DM Error: {e}")

@Bot.on_message(filters.command("users") & filters.private & filters.user(ADMINS))
async def total_users(c, m):
    count = await Data.count_documents({})
    await m.reply_text(f"Total Users in Database: {count}")

@Bot.on_message(filters.command("broadcast") & filters.private & filters.user(ADMINS))
async def broadcast(c, m):
    if not m.reply_to_message:
        return await m.reply_text("Reply to a message to broadcast it.")
    
    msg = await m.reply_text("Broadcasting started...")
    success = 0
    failed = 0
    
    async for user in Data.find():
        try:
            await m.reply_to_message.copy(chat_id=user['id'])
            success += 1
        except:
            failed += 1
            
    await msg.edit(f"Broadcast Completed!\n\nSuccess: {success}\nFailed: {failed}")

# Main execution logic to run bot and web server concurrently
async def main():
    await start_web_server()
    await Bot.start()
    print("Telegram Bot Started!")
    # Keep the async loop running
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
