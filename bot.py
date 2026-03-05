import os
import json
import random
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes
)

TOKEN = os.environ.get("BOT_TOKEN", "")

# ─── SCORES ───────────────────────────────────────────────────────────────────
SCORES = {}

def scores_add(chat_id, user_id, name, points):
    cid, uid = str(chat_id), str(user_id)
    if cid not in SCORES:
        SCORES[cid] = {}
    if uid not in SCORES[cid]:
        SCORES[cid][uid] = {"name": name, "points": 0}
    SCORES[cid][uid]["points"] += points
    SCORES[cid][uid]["name"] = name

def scores_board(chat_id):
    cid = str(chat_id)
    if cid not in SCORES:
        return []
    players = [(v["name"], v["points"]) for v in SCORES[cid].values()]
    return sorted(players, key=lambda x: x[1], reverse=True)[:10]

def scores_reset(chat_id):
    SCORES[str(chat_id)] = {}

# ─── TRIVIA DATA ──────────────────────────────────────────────────────────────
QUESTIONS = [
    {"q": "מהי הבירה של אוסטרליה?", "opts": {"א": "סידני", "ב": "קנברה", "ג": "מלבורן", "ד": "פרת׳"}, "ans": "ב"},
    {"q": "כמה גרמים יש בקילוגרם?", "opts": {"א": "100", "ב": "500", "ג": "1000", "ד": "10000"}, "ans": "ג"},
    {"q": "מי צייר את המונה ליזה?", "opts": {"א": "מיכלאנג׳לו", "ב": "רפאל", "ג": "לאונרדו דה וינצ׳י", "ד": "פיקאסו"}, "ans": "ג"},
    {"q": "מהו כוכב הלכת הגדול ביותר?", "opts": {"א": "שבתאי", "ב": "צדק", "ג": "אורנוס", "ד": "נפטון"}, "ans": "ב"},
    {"q": "כמה צלעות יש למשושה?", "opts": {"א": "5", "ב": "6", "ג": "7", "ד": "8"}, "ans": "ב"},
    {"q": "באיזו שנה הוקמה מדינת ישראל?", "opts": {"א": "1945", "ב": "1947", "ג": "1948", "ד": "1950"}, "ans": "ג"},
    {"q": "מהו הסימול הכימי של זהב?", "opts": {"א": "Ag", "ב": "Al", "ג": "Au", "ד": "Cu"}, "ans": "ג"},
    {"q": "כמה שחקנים יש בקבוצת כדורגל?", "opts": {"א": "9", "ב": "10", "ג": "11", "ד": "12"}, "ans": "ג"},
    {"q": "מה הוא הנהר הארוך ביותר בעולם?", "opts": {"א": "האמזונס", "ב": "הנילוס", "ג": "המיסיסיפי", "ד": "היאנגצה"}, "ans": "ב"},
    {"q": "מהי עיר הבירה של יפן?", "opts": {"א": "אוסקה", "ב": "קיוטו", "ג": "טוקיו", "ד": "הירושימה"}, "ans": "ג"},
    {"q": "מי כתב את רומיאו ויוליה?", "opts": {"א": "דיקנס", "ב": "שקספיר", "ג": "מולייר", "ד": "גתה"}, "ans": "ב"},
    {"q": "מהי המדינה הגדולה ביותר בעולם?", "opts": {"א": "קנדה", "ב": "סין", "ג": "ארצות הברית", "ד": "רוסיה"}, "ans": "ד"},
    {"q": "כמה שניות יש בשעה?", "opts": {"א": "360", "ב": "3600", "ג": "36000", "ד": "600"}, "ans": "ב"},
    {"q": "מהי עיר הבירה של ברזיל?", "opts": {"א": "ריו", "ב": "סאו פאולו", "ג": "ברזיליה", "ד": "סלבדור"}, "ans": "ג"},
    {"q": "כמה עצמות יש בגוף האדם?", "opts": {"א": "186", "ב": "206", "ג": "226", "ד": "246"}, "ans": "ב"},
]

# ─── GAME STATE ───────────────────────────────────────────────────────────────
trivia = {}   # chat_id -> {q, answered, correct_count, active}
tol = {}      # chat_id -> {submissions, votes, active}
story = {}    # chat_id -> {opener, entries, last_user, active}

STORY_OPENERS = [
    "היה היה אדם שמצא מפה ישנה בעליית הגג...",
    "באחד הבקרים, כל הצבעים נעלמו מהעולם...",
    "הרובוט הראשון שקיבל רגשות החליט לפתוח קפה...",
    "הדלת שבחדר הסוד נפתחה בדיוק בחצות...",
    "הכבשה ה-13 לא הצליחה להירדם — היא ידעה משהו...",
]

def get_name(user):
    return user.first_name + (f" {user.last_name}" if user.last_name else "")

# ─── COMMANDS ─────────────────────────────────────────────────────────────────
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎮 *ברוכים הבאים ל-GameBot!*\n\n"
        "❓ /trivia — טריוויה עם ניקוד\n"
        "🤥 /truthorlie — אמת או שקר\n"
        "📖 /story — סיפור קבוצתי\n"
        "🏆 /scores — טבלת המובילים\n"
        "🔄 /reset — אפס ניקוד (אדמין)",
        parse_mode="Markdown"
    )

async def scores_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    board = scores_board(update.effective_chat.id)
    if not board:
        await update.message.reply_text("אין ניקוד עדיין — שחקו! 😄")
        return
    medals = ["🥇", "🥈", "🥉"]
    lines = ["🏆 *טבלת המובילים*\n"]
    for i, (name, pts) in enumerate(board):
        medal = medals[i] if i < 3 else f"{i+1}."
        lines.append(f"{medal} {name} — *{pts}* נקודות")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

async def reset_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    member = await ctx.bot.get_chat_member(chat_id, update.effective_user.id)
    if member.status not in ("administrator", "creator"):
        await update.message.reply_text("❌ רק אדמין יכול לאפס ניקוד.")
        return
    scores_reset(chat_id)
    await update.message.reply_text("✅ הניקוד אופס!")

# ─── TRIVIA ───────────────────────────────────────────────────────────────────
async def trivia_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in trivia and trivia[chat_id]["active"]:
        await update.message.reply_text("❓ יש שאלה פעילה! ענו עליה קודם.")
        return
    q = random.choice(QUESTIONS)
    trivia[chat_id] = {"q": q, "answered": {}, "correct_count": 0, "active": True}
    opts = "\n".join([f"{l}) {a}" for l, a in q["opts"].items()])
    await update.message.reply_text(
        f"❓ *{q['q']}*\n\n{opts}\n\n⏱ יש לכם 30 שניות! ענו באות בלבד (א/ב/ג/ד)",
        parse_mode="Markdown"
    )
    async def auto_reveal():
        await asyncio.sleep(30)
        if chat_id in trivia and trivia[chat_id]["active"]:
            ans_key = trivia[chat_id]["q"]["ans"]
            ans_text = trivia[chat_id]["q"]["opts"][ans_key]
            trivia[chat_id]["active"] = False
            await ctx.bot.send_message(chat_id, f"⏰ הזמן עבר!\n✅ התשובה: *{ans_key}) {ans_text}*", parse_mode="Markdown")
    asyncio.create_task(auto_reveal())

async def handle_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in trivia or not trivia[chat_id]["active"]:
        return
    user = update.effective_user
    uid = user.id
    name = get_name(user)
    text = update.message.text.strip().upper()
    game = trivia[chat_id]
    if uid in game["answered"]:
        return
    game["answered"][uid] = text
    correct = game["q"]["ans"]
    if text == correct:
        pts = 50 if game["correct_count"] == 0 else 30 if game["correct_count"] == 1 else 20
        game["correct_count"] += 1
        scores_add(chat_id, uid, name, pts)
        ans_text = game["q"]["opts"][correct]
        await update.message.reply_text(
            f"✅ נכון, {name}! +{pts} נקודות 🎉\nהתשובה: *{correct}) {ans_text}*",
            parse_mode="Markdown"
        )
        game["active"] = False
    else:
        await update.message.reply_text(f"❌ לא נכון, {name}. נסו שוב!")

# ─── TRUTH OR LIE ─────────────────────────────────────────────────────────────
async def tol_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    tol[chat_id] = {"submissions": [], "votes": {}, "active": True}
    await update.message.reply_text(
        "🤥 *אמת או שקר התחיל!*\n\n"
        "כל אחד שולח עובדה על עצמו:\n"
        "`/tol_submit כאן כותבים עובדה`\n\n"
        "אחר כך `/tol_reveal` לחשיפה!",
        parse_mode="Markdown"
    )

async def tol_submit(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in tol or not tol[chat_id]["active"]:
        await update.message.reply_text("אין משחק פעיל. /truthorlie להתחלה")
        return
    if not ctx.args:
        await update.message.reply_text("כתוב: `/tol_submit העובדה שלך`", parse_mode="Markdown")
        return
    user = update.effective_user
    name = get_name(user)
    text = " ".join(ctx.args)
    is_truth = random.choice([True, False])
    tol[chat_id]["submissions"].append((user.id, name, text, is_truth))
    await update.message.reply_text(f"✅ {name}, נשמר! 🤫")

async def tol_reveal(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in tol or not tol[chat_id]["active"]:
        await update.message.reply_text("אין משחק פעיל.")
        return
    subs = tol[chat_id]["submissions"]
    if len(subs) < 2:
        await update.message.reply_text("צריך לפחות 2 שחקנים!")
        return
    for i, (uid, name, text, is_truth) in enumerate(subs):
        kb = [[
            InlineKeyboardButton("✅ אמת", callback_data=f"tol_{i}_true_{uid}"),
            InlineKeyboardButton("❌ שקר", callback_data=f"tol_{i}_false_{uid}")
        ]]
        await ctx.bot.send_message(
            chat_id,
            f"🤔 *עובדה #{i+1}* (מאת: {name})\n\n_{text}_",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="Markdown"
        )

async def tol_vote(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    if chat_id not in tol:
        return
    data = query.data.split("_")
    idx, vote, subject_id = int(data[1]), data[2], int(data[3])
    voter = query.from_user
    voter_name = get_name(voter)
    if voter.id == subject_id:
        await query.answer("לא יכול להצביע על עצמך! 😄", show_alert=True)
        return
    key = (voter.id, idx)
    if key in tol[chat_id]["votes"]:
        await query.answer("כבר הצבעת!", show_alert=True)
        return
    tol[chat_id]["votes"][key] = (vote, voter_name)
    votes_for = {k: v for k, v in tol[chat_id]["votes"].items() if k[1] == idx}
    if len(votes_for) >= 3:
        is_truth = tol[chat_id]["submissions"][idx][3]
        correct_ans = "true" if is_truth else "false"
        ans_text = "אמת ✅" if is_truth else "שקר ❌"
        winners = [vname for (_, i), (ans, vname) in tol[chat_id]["votes"].items() if i == idx and ans == correct_ans]
        for (vid, i), (ans, vname) in tol[chat_id]["votes"].items():
            if i == idx and ans == correct_ans and vid != subject_id:
                scores_add(chat_id, vid, vname, 20)
        winners_text = ", ".join(winners) if winners else "אף אחד"
        await query.edit_message_text(
            f"{query.message.text}\n\n🎯 *התשובה: {ans_text}*\nניחשו נכון: {winners_text} (+20 נק׳)",
            parse_mode="Markdown"
        )

# ─── STORY ────────────────────────────────────────────────────────────────────
async def story_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    opener = random.choice(STORY_OPENERS)
    story[chat_id] = {"opener": opener, "entries": [], "last_user": None, "active": True}
    await update.message.reply_text(
        f"📖 *סיפור קבוצתי התחיל!*\n\n_{opener}_\n\n"
        f"המשיכו עם: `/story_add המשפט שלכם`\n"
        f"קריאה: /story_read | סיום: /story_end",
        parse_mode="Markdown"
    )

async def story_add(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in story or not story[chat_id]["active"]:
        await update.message.reply_text("אין סיפור פעיל. /story להתחלה")
        return
    if not ctx.args:
        await update.message.reply_text("כתוב: `/story_add המשפט שלך`", parse_mode="Markdown")
        return
    user = update.effective_user
    name = get_name(user)
    if story[chat_id]["last_user"] == user.id:
        await update.message.reply_text("⏳ תן לאחרים להוסיף קודם! 😄")
        return
    text = " ".join(ctx.args)
    story[chat_id]["entries"].append((user.id, name, text))
    story[chat_id]["last_user"] = user.id
    scores_add(chat_id, user.id, name, 10)
    count = len(story[chat_id]["entries"])
    extra = f"\n\n🎲 _וואו {count} משפטים! לאן הסיפור הולך?!_" if count % 5 == 0 else ""
    await update.message.reply_text(f"✍️ {name}: _{text}_ +10 נק׳{extra}", parse_mode="Markdown")

async def story_read(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in story:
        await update.message.reply_text("אין סיפור פעיל.")
        return
    parts = [story[chat_id]["opener"]] + [t for _, _, t in story[chat_id]["entries"]]
    await update.message.reply_text(f"📖 *הסיפור:*\n\n_{' '.join(parts)}_", parse_mode="Markdown")

async def story_end(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in story:
        await update.message.reply_text("אין סיפור פעיל.")
        return
    parts = [story[chat_id]["opener"]] + [t for _, _, t in story[chat_id]["entries"]]
    story[chat_id]["active"] = False
    await update.message.reply_text(
        f"📖 *הסיפור הושלם! 🎉*\n\n_{' '.join(parts)}_\n\n{len(story[chat_id]['entries'])} משפטים. כל הכבוד!",
        parse_mode="Markdown"
    )

# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("scores", scores_cmd))
    app.add_handler(CommandHandler("reset", reset_cmd))
    app.add_handler(CommandHandler("trivia", trivia_cmd))
    app.add_handler(CommandHandler("truthorlie", tol_cmd))
    app.add_handler(CommandHandler("tol_submit", tol_submit))
    app.add_handler(CommandHandler("tol_reveal", tol_reveal))
    app.add_handler(CallbackQueryHandler(tol_vote, pattern="^tol_"))
    app.add_handler(CommandHandler("story", story_cmd))
    app.add_handler(CommandHandler("story_add", story_add))
    app.add_handler(CommandHandler("story_read", story_read))
    app.add_handler(CommandHandler("story_end", story_end))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("🤖 GameBot רץ!")
    app.run_polling()

if __name__ == "__main__":
    main()
