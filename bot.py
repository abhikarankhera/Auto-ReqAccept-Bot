import os
import sys
import time
import asyncio
from flask import Flask
from threading import Thread
from motor.motor_asyncio import AsyncIOMotorClient

# ==========================================
# 1. PYTHON 3.14 EVENT LOOP LIFE CYCLE FIX
# ==========================================
try:
    asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

# ==========================================
# 2. NATIVE CLEAN DEPENDENCY IMPORTS
# ==========================================
from hydrogram import Client, filters
from hydrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from hydrogram.errors import (
    InputUserDeactivated, 
    UserNotParticipant, 
    FloodWait, 
    UserIsBlocked, 
    PeerIdInvalid
)

# ==========================================
# 3. ENVIRONMENT VARIABLES & SETTINGS
# ==========================================
API_ID = int(os.environ.get('API_ID', 0))
API_HASH = os.environ.get('API_HASH', '')
BOT_TOKEN = os.environ.get('BOT_TOKEN', '')
DB_URL = os.environ.get('DB_URL', '')
ADMINS = int(os.environ.get('ADMINS', 0))

START_TEXT = "Hello {}!\n\nI am an automatic chat join request accepter bot. Add me into your channels or groups to get started."

if not API_ID or not API_HASH or not BOT_TOKEN or not DB_URL or not ADMINS:
    print("CRITICAL CONFIG ERROR: Ensure all environment variables (API_ID, API_HASH, BOT_TOKEN, DB_URL, ADMINS) are properly set in Render configuration.")
    sys.exit(1)

# Initialize Database Natively
Dbclient = AsyncIOMotorClient(DB_URL)
Cluster = Dbclient['Cluster0']
Data = Cluster['users']

# ==========================================
# 4. RENDER HEALTH CHECK SERVER (FLASK)
# ==========================================
app = Flask(__name__)

@app.route('/')
@app.route('/health')
def health():
    return "Auto-Accept Request Bot Engine is Live!", 200

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# ==========================================
# 5. INITIALIZE HYDROGRAM CLIENT
# ==========================================
Bot = Client(
    name='AutoAcceptBot', 
    api_id=API_ID, 
    api_hash=API_HASH, 
    bot_token=BOT_TOKEN
)

# ==========================================
# 6. SYSTEM COMMAND HANDLERS & FILTERS
# ==========================================

@Bot.on_message(filters.command("start") & filters.private)
async def start_handler(c, m):
    user_id = m.from_user.id
    if not await Data.find_one({'id': user_id}):
        await Data.insert_one({'id': user_id})
        
    button = [[
        InlineKeyboardButton('Updates', url='https://t.me/mkn_bots_updates'),
        InlineKeyboardButton('Support', url='https://t.me/MKN_BOTZ_DISCUSSION_GROUP')
    ]]
    return await m.reply_text(
        text=START_TEXT.format(m.from_user.mention), 
        disable_web_page_preview=True, 
        reply_markup=InlineKeyboardMarkup(button)
    )

@Bot.on_message(filters.command(["broadcast", "users"]) & filters.user(ADMINS))
async def broadcast(c, m):
    if m.text == "/users":
        total_users = await Data.count_documents({})
        return await m.reply(f"Total Users in DB: {total_users}")
        
    if not m.reply_to_message:
        return await m.reply_text("Please reply to a message to broadcast it.")
        
    b_msg = m.reply_to_message
    sts = await m.reply_text("Broadcasting your message to database users...")
    
    users = Data.find({})
    total_users = await Data.count_documents({})
    done = 0
    failed = 0
    success = 0
    
    async for user in users:
        user_id = int(user['id'])
        try:
            await b_msg.copy(chat_id=user_id)
            success += 1
        except FloodWait as e:
            await asyncio.sleep(e.value)
            await b_msg.copy(chat_id=user_id)
            success += 1
        except (InputUserDeactivated, UserIsBlocked, PeerIdInvalid):
            await Data.delete_many({'id': user_id})
            failed += 1
        except Exception:
            failed += 1
        done += 1
        
    return await sts.edit(f"**Broadcast Completed!**\n\nTotal Users: {total_users}\nSuccess: {success}\nFailed/Cleaned: {failed}")

# ==========================================
# 7. CHAT JOIN REQUEST LOGIC
# ==========================================
@Bot.on_chat_join_request()
async def auto_accept_join_request(c, r):
    user_id = r.from_user.id
    chat_id = r.chat.id
    try:
        await c.approve_chat_join_request(chat_id, user_id)
        # Try to register user in DB if they aren't already there
        if not await Data.find_one({'id': user_id}):
            await Data.insert_one({'id': user_id})
    except Exception as e:
        print(f"Error accepting request for user {user_id} in chat {chat_id}: {e}")

# ==========================================
# 8. PROCESS RUNTIME EXECUTION
# ==========================================
if __name__ == "__main__":
    print("Starting up background health check monitor for Render...")
    web_thread = Thread(target=run_web_server, daemon=True)
    web_thread.start()

    print("Booting Auto-Accept Bot Infrastructure...")
    Bot.run()
