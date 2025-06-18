import asyncio
from contextlib import suppress
from string import ascii_lowercase
from typing import Union

from config import BANNED_USERS
from pyrogram import filters
from pyrogram.enums import ChatMembersFilter, ChatMemberStatus, ChatType
from pyrogram.types import (
    CallbackQuery,
    ChatPermissions,
    ChatPrivileges,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from BrandrdXMusic import app
from BrandrdXMusic.core.mongo import mongodb
from BrandrdXMusic.misc import SUDOERS
from BrandrdXMusic.utils import extract_user

warnsdb = mongodb.warns

# Define extract_user_and_reason with better error handling
async def extract_user_and_reason(message: Message, sender_chat=False):
    args = message.text.strip().split()
    text = message.text
    user = None
    reason = None
    
    # If there's a reply
    if message.reply_to_message:
        reply = message.reply_to_message
        if not reply.from_user:
            if reply.sender_chat and reply.sender_chat != message.chat.id and sender_chat:
                id_ = reply.sender_chat.id
            else:
                return None, None
        else:
            id_ = reply.from_user.id
        reason = None if len(args) < 2 else text.split(None, 1)[1]
        try:
            user = await app.get_users(id_)
        except Exception as e:
            return None, f"Failed to fetch user: {str(e)}"
    # If there's a mention or ID in the command
    elif len(args) >= 2:
        if args[1].startswith("@"):
            try:
                user = await app.get_users(args[1])
            except Exception as e:
                return None, f"Failed to fetch user: {str(e)}"
        else:
            try:
                user = await app.get_users(int(args[1]))
            except (ValueError, IndexError) as e:
                return None, f"Invalid user ID: {str(e)}"
        reason = text.split(None, 2)[2] if len(args) > 2 else None
    return user.id if user else None, reason

# Simple time_converter function since original not found
async def time_converter(message: Message, time_value: str) -> int:
    import time
    unit = time_value[-1].lower()
    value = int(time_value[:-1])
    if unit == "s":
        return int(time.time()) + value
    elif unit == "m":
        return int(time.time()) + (value * 60)
    elif unit == "h":
        return int(time.time()) + (value * 3600)
    elif unit == "d":
        return int(time.time()) + (value * 86400)
    else:
        await message.reply_text("Invalid time format. Use s, m, h, or d (e.g., 5m, 2h).")
        raise ValueError("Invalid time format")

# Define ikb function since BrandrdXMusic.utils.keyboard is missing
def ikb(data: dict) -> InlineKeyboardMarkup:
    keyboard = []
    for key, value in data.items():
        keyboard.append([InlineKeyboardButton(text=key, callback_data=value)])
    return InlineKeyboardMarkup(keyboard)

__MODULE__ = "Bᴀɴ"
__HELP__ = """
/ban - Ban A User
/sban - Delete all messages of user that sended in group and ban the user
/tban - Ban A User For Specific Time
/unban - Unban A User
/warn - Warn A User
/swarn - Delete all the message sended in group and warn the user
/rmwarns - Remove All Warning of A User
/warns - Show Warning Of A User
/kick - Kick A User
/skick - Delete the replied message kicking its sender
/purge - Purge Messages
/purge [n] - Purge "n" number of messages from replied message
/del - Delete Replied Message
/promote - Promote A Member
/fullpromote - Promote A Member With All Rights
/demote - Demote A Member
/pin - Pin A Message
/unpin - unpin a message
/unpinall - unpinall messages
/mute - Mute A User
/tmute - Mute A User For Specific Time
/unmute - Unmute A User
/zombies - Ban Deleted Accounts
/report | @admins | @admin - Report A Message To Admins.
/link - Send in Group/SuperGroup Invite Link."""

async def int_to_alpha(user_id: int) -> str:
    alphabet = list(ascii_lowercase)[:10]
    text = ""
    user_id = str(user_id)
    for i in user_id:
        text += alphabet[int(i)]
    return text

async def get_warns_count() -> dict:
    chats_count = 0
    warns_count = 0
    async for chat in warnsdb.find({"chat_id": {"$lt": 0}}):
        for user in chat["warns"]:
            warns_count += chat["warns"][user]["warns"]
        chats_count += 1
    return {"chats_count": chats_count, "warns_count": warns_count}

async def get_warns(chat_id: int) -> dict[str, int]:
    warns = await warnsdb.find_one({"chat_id": chat_id})
    if not warns:
        return {}
    return warns["warns"]

async def get_warn(chat_id: int, name: str) -> Union[bool, dict]:
    name = name.lower().strip()
    warns = await get_warns(chat_id)
    if name in warns:
        return warns[name]

async def add_warn(chat_id: int, name: str, warn: dict):
    name = name.lower().strip()
    warns = await get_warns(chat_id)
    warns[name] = warn
    await warnsdb.update_one(
        {"chat_id": chat_id}, {"$set": {"warns": warns}}, upsert=True
    )

async def remove_warns(chat_id: int, name: str) -> bool:
    warnsd = await get_warns(chat_id)
    name = name.lower().strip()
    if name in warnsd:
        del warnsd[name]
        await warnsdb.update_one(
            {"chat_id": chat_id},
            {"$set": {"warns": warnsd}},
            upsert=True,
        )
        return True
    return False

async def member_permissions(chat_id: int, user_id: int):
    try:
        member = await app.get_chat_member(chat_id, user_id)
        return member.privileges.__dict__ if member.privileges else {}
    except Exception:
        return {}

@app.on_message(filters.command(["kick", "skick"]) & ~filters.private & ~BANNED_USERS)
async def kickFunc(_, message: Message):
    user_id, reason = await extract_user_and_reason(message)
    if not user_id:
        return await message.reply_text("ɪ ᴄᴀɴ'ᴛ ғɪɴᴅ ᴛʜᴀᴛ ᴜsᴇʀ")
    if isinstance(reason, str) and reason.startswith("Failed to fetch user"):
        return await message.reply_text(reason)
    if user_id == app.id:
        return await message.reply_text("ɪ ᴄᴀɴ'ᴛ ᴋɪᴄᴋ ᴍʏsᴇʟғ, ɪ ᴄᴀɴ ʟᴇᴀᴠᴇ ɪғ ʏᴏᴜ ᴡᴀɴᴛ.")
    if user_id in SUDOERS:
        return await message.reply_text("ʏᴏᴜ ᴡᴀɴɴᴀ ᴋɪᴄᴋ ᴛʜᴇ ᴇʟᴇᴠᴀᴛᴇᴅ ᴏɴᴇ ?")
    if user_id in [
        member.user.id
        async for member in app.get_chat_members(
            chat_id=message.chat.id, filter=ChatMembersFilter.ADMINISTRATORS
        )
    ]:
        return await message.reply_text(
            "ɪ ᴄᴀɴ'ᴛ ᴋɪᴄᴋ ᴀɴ ᴀᴅᴍɪɴ, ʏᴏᴜ ᴋɴᴏᴡ ᴛʜᴇ ʀᴜʟᴇs, ʏᴏᴜ ᴋɴᴏᴡ ᴛʜᴇ ʀᴜʟᴇs, sᴏ ᴅᴏ ɪ "
        )
    user = await app.get_users(user_id)
    mention = user.mention
    msg = f"""
**ᴋɪᴄᴋᴇᴅ ᴜsᴇʀ:** {mention}
**ᴋɪᴄᴋᴇᴅ ʙʏ:** {message.from_user.mention if message.from_user else 'ᴀɴᴏɴᴍᴏᴜs'}
**ʀᴇᴀsᴏɴ:** {reason or 'ɴᴏ ʀᴇᴀsᴏɴ ᴘʀᴏᴠɪᴅᴇᴅ'}"""
    await message.chat.ban_member(user_id)
    replied_message = message.reply_to_message
    if replied_message:
        message = replied_message
    await message.reply_text(msg)
    await asyncio.sleep(1)
    await message.chat.unban_member(user_id)
    if message.command[0][0] == "s":
        await message.reply_to_message.delete()

# Ban members
@app.on_message(
    filters.command(["ban", "sban", "tban"]) & ~filters.private & ~BANNED_USERS
)
async def banFunc(_, message: Message):
    user_id, reason = await extract_user_and_reason(message, sender_chat=True)
    if not user_id:
        return await message.reply_text("I can't find that user.")
    if isinstance(reason, str) and reason.startswith("Failed to fetch user"):
        return await message.reply_text(reason)
    if user_id == app.id:
        return await message.reply_text("I can't ban myself, i can leave if you want.")
    if user_id in SUDOERS:
        return await message.reply_text("You Wanna Ban The Elevated One?, RECONSIDER!")
    if user_id in [
        member.user.id
        async for member in app.get_chat_members(
            chat_id=message.chat.id, filter=ChatMembersFilter.ADMINISTRATORS
        )
    ]:
        return await message.reply_text(
            "I can't ban an admin, You know the rules, so do i."
        )
    try:
        user = await app.get_users(user_id)
        mention = user.mention
    except IndexError:
        mention = (
            message.reply_to_message.sender_chat.title
            if message.reply_to_message
            else "Anon"
        )
    msg = (
        f"**Banned User:** {mention}\n"
        f"**Banned By:** {message.from_user.mention if message.from_user else 'Anon'}\n"
    )
    if message.command[0][0] == "s":
        await message.reply_to_message.delete()
    if message.command[0] == "tban":
        split = reason.split(None, 1)
        time_value = split[0]
        temp_reason = split[1] if len(split) > 1 else ""
        temp_ban = await time_converter(message, time_value)
        msg += f"**Banned For:** {time_value}\n"
        if temp_reason:
            msg += f"**Reason:** {temp_reason}"
        with suppress(AttributeError):
            if len(time_value[:-1]) < 3:
                await message.chat.ban_member(user_id, until_date=temp_ban)
                replied_message = message.reply_to_message
                if replied_message:
                    message = replied_message
                await message.reply_text(msg)
            else:
                await message.reply_text("You can't use more than 99")
        return
    if reason:
        msg += f"**Reason:** {reason}"
    await message.chat.ban_member(user_id)
    replied_message = message.reply_to_message
    if replied_message:
        message = replied_message
    await message.reply_text(msg)

# Unban members
@app.on_message(filters.command("unban") & ~filters.private & ~BANNED_USERS)
async def unban_func(_, message: Message):
    reply = message.reply_to_message
    user_id, reason = await extract_user_and_reason(message)
    if not user_id:
        return await message.reply_text("I can't find that user.")
    if isinstance(reason, str) and reason.startswith("Failed to fetch user"):
        return await message.reply_text(reason)
    if reply and reply.sender_chat and reply.sender_chat != message.chat.id:
        return await message.reply_text("You cannot unban a channel")
    try:
        bot = await app.get_chat_member(message.chat.id, app.id)
        if not bot.privileges or not bot.privileges.can_restrict_members:
            return await message.reply_text("I don't have permission to unban members.")
        await message.chat.unban_member(user_id)
        user = await app.get_users(user_id)
        umention = user.mention
        replied_message = message.reply_to_message
        if replied_message:
            message = replied_message
        await message.reply_text(f"Unbanned! {umention}")
    except Exception as e:
        await message.reply_text(f"Failed to unban: {str(e)}")

# Promote Members
@app.on_message(
    filters.command(["promote", "fullpromote"]) & ~filters.private & ~BANNED_USERS
)
async def promoteFunc(_, message: Message):
    user_id, _ = await extract_user_and_reason(message)
    if not user_id:
        return await message.reply_text("I can't find that user.")
    bot = (await app.get_chat_member(message.chat.id, app.id)).privileges
    if user_id == app.id:
        return await message.reply_text("I can't promote myself.")
    if not bot:
        return await message.reply_text("I'm not an admin in this chat.")
    if not bot.can_promote_members:
        return await message.reply_text("I don't have enough permissions to promote members.")
    try:
        user = await app.get_users(user_id)
        if not user:
            return await message.reply_text("Unable to fetch user details.")
        umention = user.mention
        if message.command[0][0] == "f":
            await message.chat.promote_member(
                user_id=user_id,
                privileges=ChatPrivileges(
                    can_change_info=bot.can_change_info,
                    can_invite_users=bot.can_invite_users,
                    can_delete_messages=bot.can_delete_messages,
                    can_restrict_members=bot.can_restrict_members,
                    can_pin_messages=bot.can_pin_messages,
                    can_promote_members=bot.can_promote_members,
                    can_manage_chat=bot.can_manage_chat,
                    can_manage_video_chats=bot.can_manage_video_chats,
                ),
            )
            return await message.reply_text(f"Fully Promoted! {umention}")
        await message.chat.promote_member(
            user_id=user_id,
            privileges=ChatPrivileges(
                can_change_info=False,
                can_invite_users=bot.can_invite_users,
                can_delete_messages=bot.can_delete_messages,
                can_restrict_members=False,
                can_pin_messages=False,
                can_promote_members=False,
                can_manage_chat=bot.can_manage_chat,
                can_manage_video_chats=bot.can_manage_video_chats,
            ),
        )
        await message.reply_text(f"Promoted! {umention}")
    except Exception as e:
        await message.reply_text(f"Failed to promote: {str(e)}")

# Demote Member
@app.on_message(filters.command("purge") & ~filters.private)
async def purgeFunc(_, message: Message):
    repliedmsg = message.reply_to_message
    await message.delete()
    if not repliedmsg:
        return await message.reply_text("Reply to a message to purge from.")
    cmd = message.command
    if len(cmd) > 1 and cmd[1].isdigit():
        purge_to = repliedmsg.id + int(cmd[1])
        if purge_to > message.id:
            purge_to = message.id
    else:
        purge_to = message.id
    chat_id = message.chat.id
    message_ids = []
    for message_id in range(
        repliedmsg.id,
        purge_to,
    ):
        message_ids.append(message_id)
        if len(message_ids) == 100:
            await app.delete_messages(
                chat_id=chat_id,
                message_ids=message_ids,
                revoke=True,
            )
            message_ids = []
    if len(message_ids) > 0:
        await app.delete_messages(
            chat_id=chat_id,
            message_ids=message_ids,
            revoke=True,
        )

@app.on_message(filters.command("del") & ~filters.private)
async def deleteFunc(_, message: Message):
    if not message.reply_to_message:
        return await message.reply_text("Reply To A Message To Delete It")
    await message.reply_to_message.delete()
    await message.delete()

@app.on_message(filters.command("demote") & ~filters.private & ~BANNED_USERS)
async def demote(_, message: Message):
    user_id, _ = await extract_user_and_reason(message)
    if not user_id:
        return await message.reply_text("I can't find that user.")
    if user_id == app.id:
        return await message.reply_text("I can't demote myself.")
    if user_id in SUDOERS:
        return await message.reply_text(
            "You wanna demote the elevated one?, RECONSIDER!"
        )
    try:
        bot = await app.get_chat_member(message.chat.id, app.id)
        if not bot.privileges or not bot.privileges.can_promote_members:
            return await message.reply_text("I don't have permission to demote members.")
        member = await app.get_chat_member(message.chat.id, user_id)
        if member.status == ChatMemberStatus.ADMINISTRATOR:
            await message.chat.promote_member(
                user_id=user_id,
                privileges=ChatPrivileges(
                    can_change_info=False,
                    can_invite_users=False,
                    can_delete_messages=False,
                    can_restrict_members=False,
                    can_pin_messages=False,
                    can_promote_members=False,
                    can_manage_chat=False,
                    can_manage_video_chats=False,
                ),
            )
            user = await app.get_users(user_id)
            umention = user.mention
            await message.reply_text(f"Demoted! {umention}")
        else:
            await message.reply_text("The person you mentioned is not an admin.")
    except Exception as e:
        await message.reply_text(f"Failed to demote: {str(e)}")

# Pin Messages
@app.on_message(filters.command(["unpinall"]) & filters.group & ~BANNED_USERS)
async def pin(_, message: Message):
    if message.command[0] == "unpinall":
        return await message.reply_text(
            "Aʀᴇ ʏᴏᴜ sᴜʀᴇ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴜɴᴘɪɴ ᴀʟʟ ᴍᴇssᴀɢᴇs?",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(text="ʏᴇs", callback_data="unpin_yes"),
                        InlineKeyboardButton(text="ɴᴏ", callback_data="unpin_no"),
                    ],
                ]
            ),
        )

@app.on_callback_query(filters.regex(r"unpin_(yes|no)"))
async def callback_query_handler(_, query: CallbackQuery):
    if query.data == "unpin_yes":
        await app.unpin_all_chat_messages(query.message.chat.id)
        return await query.message.edit_text("Aʟʟ ᴘɪɴɴᴇᴅ ᴍᴇssᴀɢᴇs ʜᴀᴠᴇ ʙᴇᴇɴ ᴜɴᴘɪɴɴᴇᴅ.")
    elif query.data == "unpin_no":
        return await query.message.edit_text(
            "Uɴᴘɪɴ ᴏғ ᴀʟʟ ᴘɪɴɴᴇᴅ ᴍᴇssᴀɢᴇs ʜᴀs ʙᴇᴇɴ ᴄᴀɴᴄᴇʟʟᴇᴅ."
        )

@app.on_message(filters.command(["pin", "unpin"]) & ~filters.private & ~BANNED_USERS)
async def pin(_, message: Message):
    if not message.reply_to_message:
        return await message.reply_text("Reply to a message to pin/unpin it.")
    r = message.reply_to_message
    if message.command[0][0] == "u":
        await r.unpin()
        return await message.reply_text(
            f"Unpinned [this]({r.link}) message.",
            disable_web_page_preview=True,
        )
    await r.pin(disable_notification=True)
    await message.reply(
        f"Pinned [this]({r.link}) message.",
        disable_web_page_preview=True,
    )

# Mute members
@app.on_message(filters.command(["mute", "tmute"]) & ~filters.private & ~BANNED_USERS)
async def mute(_, message: Message):
    user_id, reason = await extract_user_and_reason(message)
    if not user_id:
        return await message.reply_text("I can't find that user.")
    if isinstance(reason, str) and reason.startswith("Failed to fetch user"):
        return await message.reply_text(reason)
    if user_id == app.id:
        return await message.reply_text("I can't mute myself.")
    if user_id in SUDOERS:
        return await message.reply_text("You wanna mute the elevated one?, RECONSIDER!")
    if user_id in [
        member.user.id
        async for member in app.get_chat_members(
            chat_id=message.chat.id, filter=ChatMembersFilter.ADMINISTRATORS
        )
    ]:
        return await message.reply_text(
            "I can't mute an admin, You know the rules, so do i."
        )
    try:
        bot = await app.get_chat_member(message.chat.id, app.id)
        if not bot.privileges or not bot.privileges.can_restrict_members:
            return await message.reply_text("I don't have permission to mute members.")
        user = await app.get_users(user_id)
        mention = user.mention
        keyboard = ikb({"🚨  Unmute  🚨": f"unmute_{user_id}"})
        msg = (
            f"**Muted User:** {mention}\n"
            f"**Muted By:** {message.from_user.mention if message.from_user else 'Anon'}\n"
        )
        if message.command[0] == "tmute":
            split = reason.split(None, 1)
            time_value = split[0]
            temp_reason = split[1] if len(split) > 1 else ""
            temp_mute = await time_converter(message, time_value)
            msg += f"**Muted For:** {time_value}\n"
            if temp_reason:
                msg += f"**Reason:** {temp_reason}"
            try:
                if len(time_value[:-1]) < 3:
                    await message.chat.restrict_member(
                        user_id,
                        permissions=ChatPermissions(),
                        until_date=temp_mute,
                    )
                    replied_message = message.reply_to_message
                    if replied_message:
                        message = replied_message
                    await message.reply_text(msg, reply_markup=keyboard)
                else:
                    await message.reply_text("You can't use more than 99")
            except AttributeError:
                pass
            return
        if reason:
            msg += f"**Reason:** {reason}"
        await message.chat.restrict_member(user_id, permissions=ChatPermissions())
        replied_message = message.reply_to_message
        if replied_message:
            message = replied_message
        await message.reply_text(msg, reply_markup=keyboard)
    except Exception as e:
        await message.reply_text(f"Failed to mute: {str(e)}")

@app.on_message(filters.command("unmute") & ~filters.private & ~BANNED_USERS)
async def unmute(_, message: Message):
    user_id, _ = await extract_user_and_reason(message)
    if not user_id:
        return await message.reply_text("I can't find that user.")
    try:
        bot = await app.get_chat_member(message.chat.id, app.id)
        if not bot.privileges or not bot.privileges.can_restrict_members:
            return await message.reply_text("I don't have permission to unmute members.")
        await message.chat.unban_member(user_id)
        user = await app.get_users(user_id)
        umention = user.mention
        replied_message = message.reply_to_message
        if replied_message:
            message = replied_message
        await message.reply_text(f"Unmuted! {umention}")
    except Exception as e:
        await message.reply_text(f"Failed to unmute: {str(e)}")

# Zombies (Ban Deleted Accounts)
@app.on_message(filters.command("zombies") & ~filters.private & ~BANNED_USERS)
async def zombies(_, message: Message):
    chat_id = message.chat.id
    deleted_users = []
    async for member in app.get_chat_members(chat_id):
        if member.user.is_deleted:
            deleted_users.append(member.user.id)
    if not deleted_users:
        return await message.reply_text("No deleted accounts found in this chat.")
    banned_count = 0
    for user_id in deleted_users:
        try:
            await message.chat.ban_member(user_id)
            banned_count += 1
        except Exception:
            continue
    await message.reply_text(f"Banned {banned_count} deleted accounts (zombies).")

# Report
@app.on_message(filters.command(["report", "admins", "admin"]) & ~filters.private & ~BANNED_USERS)
async def report(_, message: Message):
    if not message.reply_to_message:
        return await message.reply_text("Reply to a message to report it to admins.")
    reported_message = message.reply_to_message
    reported_user = reported_message.from_user
    if not reported_user:
        return await message.reply_text("Cannot report this message (no user found).")
    if reported_user.id == message.from_user.id:
        return await message.reply_text("You can't report your own message!")
    admins = []
    async for member in app.get_chat_members(
        chat_id=message.chat.id, filter=ChatMembersFilter.ADMINISTRATORS
    ):
        if member.user.id != app.id:  # Exclude the bot itself
            admins.append(f"[{member.user.first_name}](tg://user?id={member.user.id})")
    if not admins:
        return await message.reply_text("No admins found in this chat to report to.")
    admin_list = ", ".join(admins)
    report_text = (
        f"**Reported by:** {message.from_user.mention}\n"
        f"**Reported user:** {reported_user.mention}\n"
        f"**Admins:** {admin_list}"
    )
    await message.reply_text(report_text, disable_web_page_preview=True)

@app.on_message(filters.command(["warn", "swarn"]) & ~filters.private & ~BANNED_USERS)
async def warn_user(_, message: Message):
    user_id, reason = await extract_user_and_reason(message)
    chat_id = message.chat.id
    if not user_id:
        return await message.reply_text("ɪ ᴄᴀɴᴛ ғɪɴᴅ ᴛʜᴀᴛ ᴜsᴇʀ")
    if isinstance(reason, str) and reason.startswith("Failed to fetch user"):
        return await message.reply_text(reason)
    if user_id == app.id:
        return await message.reply_text("ɪ ᴄᴀɴ'ᴛ ᴡᴀʀɴ ᴍʏsᴇʟғ, ɪ ᴄᴀɴ ʟᴇᴀᴠᴇ ɪғ ʏᴏᴜ ᴡᴀɴᴛ.")
    if user_id in SUDOERS:
        return await message.reply_text(
            "ɪ ᴄᴀɴ'ᴛ ᴡᴀʀɴ ᴍʏ ᴍᴀɴᴀɢᴇʀ's, ʙᴇᴄᴀᴜsᴇ ʜᴇ ᴍᴀɴᴀɢᴇ ᴍᴇ!"
        )
    if user_id in [
        member.user.id
        async for member in app.get_chat_members(
            chat_id=message.chat.id, filter=ChatMembersFilter.ADMINISTRATORS
        )
    ]:
        return await message.reply_text(
            "ɪ ᴄᴀɴ'ᴛ ᴡᴀʀɴ ᴀɴ ᴀᴅᴍɪɴ, ʏᴏᴜ ᴋɴᴏᴡ ᴛʜᴇ ʀᴜʟᴇs sᴏ ᴅᴏ ɪ."
        )
    try:
        bot = await app.get_chat_member(message.chat.id, app.id)
        if not bot.privileges or not bot.privileges.can_restrict_members:
            return await message.reply_text("I don't have permission to warn members.")
        user = await app.get_users(user_id)
        mention = user.mention
        keyboard = ikb({"🚨  ʀᴇᴍᴏᴠᴇ ᴡᴀʀɴ  🚨": f"unwarn_{user_id}"})
        warns = await get_warn(chat_id, await int_to_alpha(user_id))
        if warns:
            warns = warns["warns"]
        else:
            warns = 0
        if message.command[0][0] == "s":
            await message.reply_to_message.delete()
        if warns >= 2:
            await message.chat.ban_member(user_id)
            await message.reply_text(f"ɴᴜᴍʙᴇʀ ᴏғ ᴡᴀʀɴs ᴏғ {mention} ᴇxᴄᴇᴇᴅᴇᴅ, ʙᴀɴɴᴇᴅ!")
            await remove_warns(chat_id, await int_to_alpha(user_id))
        else:
            warn = {"warns": warns + 1}
            msg = f"""
**ᴡᴀʀɴᴇᴅ ᴜsᴇʀ:** {mention}
**ᴡᴀʀɴᴇᴅ ʙʏ:** {message.from_user.mention if message.from_user else 'ᴀɴᴏɴᴍᴏᴜs'}
**ʀᴇᴀsᴏɴ :** {reason or 'ɴᴏ ʀᴇᴀsᴏɴ ᴘʀᴏᴠᴏᴅᴇᴅ'}
**ᴡᴀʀɴs:** {warns + 1}/3"""
            replied_message = message.reply_to_message
            if replied_message:
                message = replied_message
            await message.reply_text(msg, reply_markup=keyboard)
            await add_warn(chat_id, await int_to_alpha(user_id), warn)
    except Exception as e:
        await message.reply_text(f"Failed to warn: {str(e)}")

@app.on_callback_query(filters.regex("unwarn_") & ~BANNED_USERS)
async def remove_warning(_, cq: CallbackQuery):
    from_user = cq.from_user
    chat_id = cq.message.chat.id
    permissions = await member_permissions(chat_id, from_user.id)
    permission = "can_restrict_members"
    if permission not in permissions:
        return await cq.answer(
            "ʏᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ ᴇɴᴏᴜɢʜ ᴘᴇʀᴍɪssɪᴏɴs ᴛᴏ ᴘᴇʀғᴏʀᴍ ᴛʜɪs ᴀᴄᴛɪᴏɴ\n"
            + f"ᴘᴇʀᴍɪssɪᴏɴ ɴᴇᴇᴅᴇᴅ: {permission}",
            show_alert=True,
        )
    user_id = cq.data.split("_")[1]
    warns = await get_warn(chat_id, await int_to_alpha(user_id))
    if warns:
        warns = warns["warns"]
    if not warns or warns == 0:
        return await cq.answer("ᴜsᴇʀ ʜᴀs ɴᴏ ᴡᴀʀɴɪɴɢs.")
    warn = {"warns": warns - 1}
    await add_warn(chat_id, await int_to_alpha(user_id), warn)
    text = cq.message.text.markdown
    text = f"~~{text}~~\n\n"
    text += f"__ᴡᴀʀɴ ʀᴇᴍᴏᴠᴇᴅ ʙʏ {from_user.mention}__"
    await cq.message.edit(text)

@app.on_message(filters.command("rmwarns") & ~filters.private & ~BANNED_USERS)
async def remove_warnings(_, message: Message):
    user_id, _ = await extract_user_and_reason(message)
    if not user_id:
        return await message.reply_text("I can't find that user.")
    try:
        bot = await app.get_chat_member(message.chat.id, app.id)
        if not bot.privileges or not bot.privileges.can_restrict_members:
            return await message.reply_text("I don't have permission to remove warnings.")
        user = await app.get_users(user_id)
        mention = user.mention
        chat_id = message.chat.id
        warns = await get_warn(chat_id, await int_to_alpha(user_id))
        if warns:
            warns = warns["warns"]
        if warns == 0 or not warns:
            await message.reply_text(f"{mention} ʜᴀs ɴᴏ ᴡᴀʀɴɪɴɢs.")
        else:
            await remove_warns(chat_id, await int_to_alpha(user_id))
            await message.reply_text(f"ʀᴇᴍᴏᴠᴇᴅ ᴡᴀʀɴɪɴɢs ᴏғ {mention}.")
    except Exception as e:
        await message.reply_text(f"Failed to remove warnings: {str(e)}")

@app.on_message(filters.command("warns") & ~filters.private & ~BANNED_USERS)
async def check_warns(_, message: Message):
    user_id, _ = await extract_user_and_reason(message)
    if not user_id:
        return await message.reply_text("ɪ ᴄᴀɴ'ᴛ ғɪɴᴅ ᴛʜᴀᴛ ᴜsᴇʀ.")
    try:
        user = await app.get_users(user_id)
        warns = await get_warn(message.chat.id, await int_to_alpha(user_id))
        mention = user.mention
        if warns:
            warns = warns["warns"]
        else:
            return await message.reply_text(f"{mention} ʜᴀs ɴᴏ ᴡᴀʀɴɪɴɢs.")
        return await message.reply_text(f"{mention} ʜᴀs {warns}/3 ᴡᴀʀɴɪɴɢs")
    except Exception as e:
        await message.reply_text(f"Failed to check warnings: {str(e)}")

@app.on_message(filters.command("link") & ~BANNED_USERS)
async def invite(_, message):
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        link = (await app.get_chat(message.chat.id)).invite_link
        if not link:
            link = await app.export_chat_invite_link(message.chat.id)
        text = f"ʜᴇʀᴇ's ᴛʜᴇ ɢʀᴏᴜᴘ ɪɴᴠɪᴛᴇ ʟɪɴᴋ \n\n{link}"
        if message.reply_to_message:
            await message.reply_to_message.reply_text(
                text, disable_web_page_preview=True
            )
        else:
            await message.reply_text(text, disable_web_page_preview=True)
