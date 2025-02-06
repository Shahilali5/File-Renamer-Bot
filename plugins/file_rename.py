import random
import asyncio
import os
import time
from pyrogram import Client, filters
from pyrogram.enums import MessageMediaType
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ForceReply
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
from helper.ffmpeg import fix_thumb, take_screen_shot
from helper.utils import progress_for_pyrogram, convert, humanbytes, add_prefix_suffix
from helper.database import db
from config import Config

app = Client("test", api_id=Config.STRING_API_ID,
             api_hash=Config.STRING_API_HASH, session_string=Config.STRING_SESSION)

@Client.on_callback_query(filters.regex('rename'))
async def rename(bot, update):
    await update.message.delete()
    await update.message.reply_text("🦋 Enter New Filename...",
                                    reply_to_message_id=update.message.reply_to_message.id,
                                    reply_markup=ForceReply(True))

@Client.on_message(filters.private & filters.reply)
async def refunc(client, message):
    reply_message = message.reply_to_message
    if isinstance(reply_message.reply_markup, ForceReply):
        new_name = message.text
        await message.delete()
        msg = await client.get_messages(message.chat.id, reply_message.id)
        file = msg.reply_to_message
        media = getattr(file, file.media.value)
        extn = media.file_name.rsplit('.', 1)[-1] if "." in media.file_name else "mkv"
        new_name = f"{new_name}.{extn}" if "." not in new_name else new_name
        await reply_message.delete()

        button = [[InlineKeyboardButton("📁 Document", callback_data="upload_document")]]
        if file.media in [MessageMediaType.VIDEO, MessageMediaType.DOCUMENT]:
            button.append([InlineKeyboardButton("🎥 Video", callback_data="upload_video")])
        elif file.media == MessageMediaType.AUDIO:
            button.append([InlineKeyboardButton("🎵 Audio", callback_data="upload_audio")])

        await message.reply(
            text=f"**Select The Output File Type**\n**• File Name:** `{new_name}`",
            reply_to_message_id=file.id,
            reply_markup=InlineKeyboardMarkup(button)
        )

@Client.on_callback_query(filters.regex("upload"))
async def doc(bot, update):
    if not os.path.isdir("Metadata"):
        os.mkdir("Metadata")

    prefix = await db.get_prefix(update.message.chat.id)
    suffix = await db.get_suffix(update.message.chat.id)
    new_name = update.message.text.split(":-")[1].strip()
    new_filename = add_prefix_suffix(new_name, prefix, suffix)
    file_path = f"downloads/{new_filename}"
    file = update.message.reply_to_message
    ms = await update.message.edit("Downloading your file...")

    try:
        path = await bot.download_media(message=file, file_name=file_path, progress=progress_for_pyrogram,
                                        progress_args=("Download started...", ms, time.time()))
    except Exception as e:
        return await ms.edit(str(e))

    _bool_metadata = await db.get_metadata(update.message.chat.id)
    metadata_path = f"Metadata/{new_filename}"
    if _bool_metadata:
        metadata = await db.get_metadata_code(update.message.chat.id)
        if metadata:
            await ms.edit("Adding metadata to file...")
            cmd = f'ffmpeg -i "{path}" {metadata} "{metadata_path}"'
            process = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE,
                                                            stderr=asyncio.subprocess.PIPE)
            _, stderr = await process.communicate()
            if stderr:
                return await ms.edit(str(stderr.decode()) + "\n\n**Error**")
            await ms.edit("Metadata added successfully! Uploading...")

    else:
        await ms.edit("Uploading...")

    duration = 0
    try:
        parser = createParser(file_path)
        metadata = extractMetadata(parser)
        duration = metadata.get('duration').seconds if metadata.has("duration") else 0
        parser.close()
    except:
        pass

    ph_path = None
    media = getattr(file, file.media.value)
    c_caption = await db.get_caption(update.message.chat.id)
    c_thumb = await db.get_thumbnail(update.message.chat.id)

    caption = c_caption.format(filename=new_filename, filesize=humanbytes(media.file_size), duration=convert(duration)) \
        if c_caption else f"**{new_filename}**"

    if c_thumb:
        ph_path = await bot.download_media(c_thumb)
        width, height, ph_path = await fix_thumb(ph_path)
    else:
        try:
            ph_path_ = await take_screen_shot(file_path, os.path.dirname(os.path.abspath(file_path)),
                                              random.randint(0, duration - 1))
            width, height, ph_path = await fix_thumb(ph_path_)
        except:
            ph_path = None

    type = update.data.split("_")[1]
    uploaded_file = None

    try:
        if type == "document":
            uploaded_file = await bot.send_document(
                update.message.chat.id, document=metadata_path if _bool_metadata else file_path,
                thumb=ph_path, caption=caption, progress=progress_for_pyrogram,
                progress_args=("Upload started...", ms, time.time()))
        elif type == "video":
            uploaded_file = await bot.send_video(
                update.message.chat.id, video=metadata_path if _bool_metadata else file_path,
                caption=caption, thumb=ph_path, width=width, height=height, duration=duration,
                progress=progress_for_pyrogram, progress_args=("Upload started...", ms, time.time()))
        elif type == "audio":
            uploaded_file = await bot.send_audio(
                update.message.chat.id, audio=metadata_path if _bool_metadata else file_path,
                caption=caption, thumb=ph_path, duration=duration,
                progress=progress_for_pyrogram, progress_args=("Upload started...", ms, time.time()))
    except Exception as e:
        os.remove(file_path)
        if ph_path: os.remove(ph_path)
        if metadata_path: os.remove(metadata_path)
        return await ms.edit(f"Error: {e}")

    if uploaded_file:
        file_id = uploaded_file.message_id
        bot_username = Config.BOT_USERNAME
        shareable_link = f"https://t.me/{bot_username}?file={file_id}"

        await ms.edit(f"✅ File uploaded successfully!\n\n📂 **Download Link:** [Click Here]({shareable_link})",
                      disable_web_page_preview=True)

    if ph_path:
        os.remove(ph_path)
    if file_path:
        os.remove(file_path)
    if metadata_path:
        os.remove(metadata_path)
  
