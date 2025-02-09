from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.errors import UserNotParticipant
from config import Config
from helper.database import db

async def not_subscribed(_, client, message):
    await db.add_user(client, message)
    
    if not Config.FORCE_SUB:
        return False  # No force subscription required

    try:             
        user = await client.get_chat_member(Config.FORCE_SUB, message.from_user.id) 
        if user.status == enums.ChatMemberStatus.BANNED:
            return True 
        return False  # User is not banned, so no restriction
    except (UserNotParticipant, KeyError):  # Catch both exceptions
        return True  # User is not a participant, so needs to subscribe


@Client.on_message(filters.private & filters.create(not_subscribed))
async def forces_sub(client, message):
    buttons = [
        [InlineKeyboardButton(text="📢 ᴊᴏɪɴ ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ", url=f"https://t.me/{Config.FORCE_SUB}")]
    ]
    
    text = "**sᴏʀʀʏ, ʏᴏᴜ'ʀᴇ ɴᴏᴛ ᴊᴏɪɴᴇᴅ ᴍʏ ᴄʜᴀɴɴᴇʟ. ᴘʟᴇᴀsᴇ ᴊᴏɪɴ ᴏᴜʀ ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ ᴛᴏ ᴄᴏɴᴛɪɴᴜᴇ.**"

    try:
        user = await client.get_chat_member(Config.FORCE_SUB, message.from_user.id)    
        if user.status == enums.ChatMemberStatus.BANNED:                                   
            return await client.send_message(
                message.from_user.id,
                text="Sᴏʀʀʏ, Yᴏᴜ'ʀᴇ Bᴀɴɴᴇᴅ Fʀᴏᴍ Uꜱɪɴɢ Tʜɪꜱ Bᴏᴛ."
            )  
    except (UserNotParticipant, KeyError):                       
        return await message.reply_text(text=text, reply_markup=InlineKeyboardMarkup(buttons))
        
