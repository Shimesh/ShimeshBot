import os
import json
import random
import asyncio
from datetime import datetime, time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes
)
from games.trivia import TriviaGame
from games.truth_or_lie import TruthOrLieGame
from games.story import StoryGame
from utils.scores import ScoreManager

TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# Active game instances per chat
trivia_games = {}
tol_games = {}
story_games = {}
score_manager = ScoreManager()

# ─── /start ───────────────────────────────────────────────────────────────────
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎮 *ברוכים הבאים ל-GameBot!*\n\n"
        "אני יכול לנהל 3 משחקים לקבוצה:\n\n"
        "❓ /trivia — טריוויה יומית עם ניקוד\n"
        "🤥 /truthorlie — אמת או שקר\n"
        "📖 /story — סיפור קבוצתי\n"
        "🏆 /scores — טבלת המובילים\n"
        "🔄 /reset — אפס ניקוד (אדמין בלבד)\n\n"
        "הוסף אותי לקבוצה ותן לי הרשאת Admin — ונתחיל! 🚀",
        parse_mode="Markdown"
    )

# ─── /scores ──────────────────────────────────────────────────────────────────
async def scores(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    board = score_manager.get_leaderboard(chat_id)
    if not board:
        await update.message.reply_text("אין ניקוד עדיין — שחקו קצת! 😄")
        return
    medals = ["🥇", "🥈", "🥉"]
    lines = ["🏆 *טבלת המובילים*\n"]
    for i, (name, pts) in enumerate(board):
        medal = medals[i] if i < 3 else f"{i+1}."
        lines.append(f"{medal} {name} — *{pts}* נקודות")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

# ─── /reset ───────────────────────────────────────────────────────────────────
async def reset_scores(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = await ctx.bot.get_chat_member(chat_id, update.effective_user.id)
    if user.status not in ("administrator", "creator"):
        await update.message.reply_text("❌ רק אדמין יכול לאפס ניקוד.")
        return
    score_manager.reset(chat_id)
    await update.message.reply_text("✅ הניקוד אופס!")

# ─── TRIVIA ───────────────────────────────────────────────────────────────────
async def trivia_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in trivia_games and trivia_games[chat_id].active:
        await update.message.reply_text("❓ יש שאלה פעילה כבר — ענו עליה קודם!")
        return
    game = TriviaGame()
    trivia_games[chat_id] = game
    q = game.start()
    opts = "\n".join([f"{l}) {a}" for l, a in q["options"].items()])
    msg = await update.message.reply_text(
        f"❓ *{q['question']}*\n\n{opts}\n\n⏱ יש לכם 30 שניות!",
        parse_mode="Markdown"
    )
    # Auto-reveal after 30s
    async def reveal():
        await asyncio.sleep(30)
        if chat_id in trivia_games and trivia_games[chat_id].active:
            game = trivia_games[chat_id]
            ans = game.correct_answer()
            game.active = False
            await ctx.bot.send_message(
                chat_id,
                f"⏰ הזמן עבר!\n✅ התשובה הנכונה: *{ans}*",
                parse_mode="Markdown"
            )
    asyncio.create_task(reveal())

async def trivia_answer(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in trivia_games or not trivia_games[chat_id].active:
        return
    game = trivia_games[chat_id]
    user = update.effective_user
    name = user.first_name + (f" {user.last_name}" if user.last_name else "")
    text = update.message.text.strip().upper()
    result = game.answer(user.id, text)
    if result == "already":
        return
    if result == "correct":
        pts = game.points_for_next()
        score_manager.add(chat_id, user.id, name, pts)
        await update.message.reply_text(
            f"✅ נכון, {name}! +{pts} נקודות 🎉\n"
            f"התשובה: *{game.correct_answer()}*",
            parse_mode="Markdown"
        )
        game.active = False
    elif result == "wrong":
        await update.message.reply_text(f"❌ לא נכון, {name}. נסו שוב!")

# ─── TRUTH OR LIE ─────────────────────────────────────────────────────────────
async def tol_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in tol_games and tol_games[chat_id].active:
        await update.message.reply_text("🤥 משחק כבר פעיל! השתמשו ב /tol_submit לשלוח עובדה.")
        return
    game = TruthOrLieGame()
    tol_games[chat_id] = game
    await update.message.reply_text(
        "🤥 *אמת או שקר — הוראות:*\n\n"
        "1️⃣ כל שחקן שולח: `/tol_submit כתבו כאן עובדה על עצמכם`\n"
        "   (אמת או שקר — אתם מחליטים!)\n"
        "2️⃣ אחרי שכולם שלחו, הבוט שולח לכולם את העובדות\n"
        "3️⃣ כולם מנחשים על כל עובדה: אמת / שקר\n"
        "4️⃣ מי שמנחש נכון מקבל נקודות!\n\n"
        "⏳ שלחו עובדות עד שמישהו כותב `/tol_reveal`",
        parse_mode="Markdown"
    )

async def tol_submit(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in tol_games or not tol_games[chat_id].active:
        await update.message.reply_text("אין משחק פעיל. התחילו עם /truthorlie")
        return
    if not ctx.args:
        await update.message.reply_text("כתבו: `/tol_submit העובדה שלכם כאן`", parse_mode="Markdown")
        return
    user = update.effective_user
    name = user.first_name + (f" {user.last_name}" if user.last_name else "")
    text = " ".join(ctx.args)
    game = tol_games[chat_id]
    game.submit(user.id, name, text)
    await update.message.reply_text(f"✅ {name}, העובדה שלך נשמרה! 🤫")

async def tol_reveal(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in tol_games or not tol_games[chat_id].active:
        await update.message.reply_text("אין משחק פעיל.")
        return
    game = tol_games[chat_id]
    if len(game.submissions) < 2:
        await update.message.reply_text("צריך לפחות 2 שחקנים! שלחו עובדות עם /tol_submit")
        return
    for i, (uid, name, text) in enumerate(game.submissions):
        keyboard = [[
            InlineKeyboardButton("✅ אמת", callback_data=f"tol_{i}_true_{uid}"),
            InlineKeyboardButton("❌ שקר", callback_data=f"tol_{i}_false_{uid}")
        ]]
        await ctx.bot.send_message(
            chat_id,
            f"🤔 *עובדה #{i+1}* (מאת: {name})\n\n_{text}_\n\nאמת או שקר?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

async def tol_vote(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    if chat_id not in tol_games:
        return
    game = tol_games[chat_id]
    data = query.data.split("_")
    idx, vote, subject_id = int(data[1]), data[2], int(data[3])
    voter = query.from_user
    voter_name = voter.first_name + (f" {voter.last_name}" if voter.last_name else "")
    if voter.id == subject_id:
        await query.answer("לא יכול להצביע על עצמך! 😄", show_alert=True)
        return
    result = game.vote(voter.id, voter_name, idx, vote)
    if result == "already":
        await query.answer("כבר הצבעת על זה!", show_alert=True)
    elif result:
        is_truth, correct_voters = result
        ans_text = "אמת ✅" if is_truth else "שקר ❌"
        pts = 20
        for vid, vname in correct_voters:
            score_manager.add(chat_id, vid, vname, pts)
        winners = ", ".join([vn for _, vn in correct_voters]) if correct_voters else "אף אחד"
        await query.edit_message_text(
            f"{query.message.text}\n\n"
            f"🎯 *התשובה: {ans_text}*\n"
            f"🏅 ניחשו נכון: {winners} (+{pts} נקודות)",
            parse_mode="Markdown"
        )

# ─── STORY ────────────────────────────────────────────────────────────────────
async def story_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in story_games and story_games[chat_id].active:
        await update.message.reply_text("📖 סיפור כבר בתהליך! שלחו `/story_add המשפט שלכם`", parse_mode="Markdown")
        return
    starters = [
        "היה היה אדם שמצא מפה ישנה בעליית הגג...",
        "באחד הבקרים, כל הצבעים נעלמו מהעולם...",
        "הרובוט הראשון שקיבל רגשות החליט לפתוח קפה...",
        "הדלת שבחדר הסוד נפתחה בדיוק בחצות...",
        "הכבשה ה-13 לא הצליחה להירדם — היא ידעה משהו...",
    ]
    opener = random.choice(starters)
    game = StoryGame(opener)
    story_games[chat_id] = game
    await update.message.reply_text(
        f"📖 *סיפור קבוצתי התחיל!*\n\n"
        f"_{opener}_\n\n"
        f"➕ המשיכו את הסיפור עם:\n`/story_add המשפט שלכם כאן`\n\n"
        f"כל תרומה = 10 נקודות!\n"
        f"כדי לראות את הסיפור המלא: /story_read",
        parse_mode="Markdown"
    )

async def story_add(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in story_games or not story_games[chat_id].active:
        await update.message.reply_text("אין סיפור פעיל. התחילו עם /story")
        return
    if not ctx.args:
        await update.message.reply_text("כתבו: `/story_add המשפט שלכם כאן`", parse_mode="Markdown")
        return
    user = update.effective_user
    name = user.first_name + (f" {user.last_name}" if user.last_name else "")
    text = " ".join(ctx.args)
    game = story_games[chat_id]
    # Check same user twice in a row
    if game.last_user == user.id:
        await update.message.reply_text("⏳ תן לאחרים להוסיף קודם! 😄")
        return
    game.add(user.id, name, text)
    score_manager.add(chat_id, user.id, name, 10)
    count = len(game.entries)
    comment = ""
    if count % 5 == 0:
        comment = f"\n\n🎲 _וואו, {count} משפטים! לאן הסיפור הולך?!_"
    await update.message.reply_text(
        f"✍️ {name} הוסיף/ה: _{text}_{comment}\n\n+10 נקודות!",
        parse_mode="Markdown"
    )

async def story_read(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in story_games:
        await update.message.reply_text("אין סיפור פעיל. התחילו עם /story")
        return
    game = story_games[chat_id]
    full = game.get_full_story()
    await update.message.reply_text(
        f"📖 *הסיפור עד כה:*\n\n_{full}_",
        parse_mode="Markdown"
    )

async def story_end(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in story_games or not story_games[chat_id].active:
        await update.message.reply_text("אין סיפור פעיל.")
        return
    game = story_games[chat_id]
    full = game.get_full_story()
    game.active = False
    await update.message.reply_text(
        f"📖 *הסיפור הושלם! 🎉*\n\n_{full}_\n\n"
        f"תרמו {len(game.entries)} משפטים. כל הכבוד לכולם!",
        parse_mode="Markdown"
    )

# ─── Handle text for trivia ───────────────────────────────────────────────────
async def handle_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in trivia_games and trivia_games[chat_id].active:
        await trivia_answer(update, ctx)

# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("scores", scores))
    app.add_handler(CommandHandler("reset", reset_scores))
    # Trivia
    app.add_handler(CommandHandler("trivia", trivia_start))
    # Truth or Lie
    app.add_handler(CommandHandler("truthorlie", tol_start))
    app.add_handler(CommandHandler("tol_submit", tol_submit))
    app.add_handler(CommandHandler("tol_reveal", tol_reveal))
    app.add_handler(CallbackQueryHandler(tol_vote, pattern="^tol_"))
    # Story
    app.add_handler(CommandHandler("story", story_start))
    app.add_handler(CommandHandler("story_add", story_add))
    app.add_handler(CommandHandler("story_read", story_read))
    app.add_handler(CommandHandler("story_end", story_end))
    # Text messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("🤖 GameBot רץ!")
    app.run_polling()

if __name__ == "__main__":
    main()
