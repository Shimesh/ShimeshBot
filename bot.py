import os
import random
import asyncio
from datetime import time as dtime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes
)

TOKEN = os.environ.get("BOT_TOKEN", "")

QUESTIONS = {
    "easy": [
        {"q": "כמה גרמים יש בקילוגרם?", "opts": {"א": "100", "ב": "500", "ג": "1000", "ד": "2000"}, "ans": "ג"},
        {"q": "כמה צלעות יש למשולש?", "opts": {"א": "2", "ב": "3", "ג": "4", "ד": "5"}, "ans": "ב"},
        {"q": "כמה שעות יש ביום?", "opts": {"א": "12", "ב": "24", "ג": "48", "ד": "36"}, "ans": "ב"},
        {"q": "כמה רגליים יש לעכביש?", "opts": {"א": "4", "ב": "6", "ג": "8", "ד": "10"}, "ans": "ג"},
        {"q": "מה הוא היונק הגדול ביותר?", "opts": {"א": "פיל", "ב": "לוויתן כחול", "ג": "ג׳ירפה", "ד": "היפופוטם"}, "ans": "ב"},
        {"q": "איזה צבע מתקבל מערבוב אדום וכחול?", "opts": {"א": "ירוק", "ב": "כתום", "ג": "סגול", "ד": "חום"}, "ans": "ג"},
        {"q": "כמה ימים יש בשבוע?", "opts": {"א": "5", "ב": "6", "ג": "7", "ד": "8"}, "ans": "ג"},
        {"q": "כמה חודשים יש בשנה?", "opts": {"א": "10", "ב": "11", "ג": "12", "ד": "13"}, "ans": "ג"},
        {"q": "מה הצבע של עלים ברוב העצים?", "opts": {"א": "אדום", "ב": "כחול", "ג": "ירוק", "ד": "צהוב"}, "ans": "ג"},
        {"q": "מה הוא הים הגדול ביותר?", "opts": {"א": "האוקיינוס האטלנטי", "ב": "האוקיינוס ההודי", "ג": "הארקטי", "ד": "האוקיינוס השקט"}, "ans": "ד"},
    ],
    "medium": [
        {"q": "מהי הבירה של אוסטרליה?", "opts": {"א": "סידני", "ב": "קנברה", "ג": "מלבורן", "ד": "פרת׳"}, "ans": "ב"},
        {"q": "מי צייר את המונה ליזה?", "opts": {"א": "מיכלאנג׳לו", "ב": "רפאל", "ג": "לאונרדו דה וינצ׳י", "ד": "פיקאסו"}, "ans": "ג"},
        {"q": "מהו כוכב הלכת הגדול ביותר?", "opts": {"א": "שבתאי", "ב": "צדק", "ג": "אורנוס", "ד": "נפטון"}, "ans": "ב"},
        {"q": "באיזו שנה הוקמה מדינת ישראל?", "opts": {"א": "1945", "ב": "1947", "ג": "1948", "ד": "1950"}, "ans": "ג"},
        {"q": "מהו הסימול הכימי של זהב?", "opts": {"א": "Ag", "ב": "Al", "ג": "Au", "ד": "Cu"}, "ans": "ג"},
        {"q": "מה הוא הנהר הארוך ביותר?", "opts": {"א": "האמזונס", "ב": "הנילוס", "ג": "המיסיסיפי", "ד": "היאנגצה"}, "ans": "ב"},
        {"q": "מי כתב את רומיאו ויוליה?", "opts": {"א": "דיקנס", "ב": "שקספיר", "ג": "מולייר", "ד": "גתה"}, "ans": "ב"},
        {"q": "מהי המדינה הגדולה ביותר?", "opts": {"א": "קנדה", "ב": "סין", "ג": "ארצות הברית", "ד": "רוסיה"}, "ans": "ד"},
        {"q": "כמה שניות יש בשעה?", "opts": {"א": "360", "ב": "3600", "ג": "36000", "ד": "600"}, "ans": "ב"},
        {"q": "מהי עיר הבירה של ברזיל?", "opts": {"א": "ריו", "ב": "סאו פאולו", "ג": "ברזיליה", "ד": "סלבדור"}, "ans": "ג"},
    ],
    "hard": [
        {"q": "מהו המספר הראשוני ה-10?", "opts": {"א": "23", "ב": "27", "ג": "29", "ד": "31"}, "ans": "ג"},
        {"q": "מי פיתח את תורת הקוואנטים?", "opts": {"א": "איינשטיין", "ב": "בוהר", "ג": "מקס פלאנק", "ד": "שרדינגר"}, "ans": "ג"},
        {"q": "מהי בירת קזחסטן?", "opts": {"א": "אלמא-אטה", "ב": "אסטנה", "ג": "טשקנט", "ד": "בישקק"}, "ans": "ב"},
        {"q": "כמה עצמות יש בגוף האדם?", "opts": {"א": "186", "ב": "196", "ג": "206", "ד": "216"}, "ans": "ג"},
        {"q": "מהו המרחק לשמש במיליון ק״מ?", "opts": {"א": "100", "ב": "150", "ג": "200", "ד": "250"}, "ans": "ב"},
        {"q": "באיזו שנה הושלם בניית הכולוסיאום?", "opts": {"א": "70 לספירה", "ב": "80 לספירה", "ג": "90 לספירה", "ד": "100 לספירה"}, "ans": "ב"},
        {"q": "מהי שפת התכנות של גוידו ון רוסום?", "opts": {"א": "Java", "ב": "Ruby", "ג": "Python", "ד": "Perl"}, "ans": "ג"},
        {"q": "כמה לוויינים טבעיים יש למאדים?", "opts": {"א": "0", "ב": "1", "ג": "2", "ד": "3"}, "ans": "ג"},
        {"q": "מי כתב את ״מלחמה ושלום״?", "opts": {"א": "דוסטויבסקי", "ב": "צ׳כוב", "ג": "טורגנייב", "ד": "טולסטוי"}, "ans": "ד"},
        {"q": "מהו הצפד הכימי של מים?", "opts": {"א": "HO", "ב": "H2O", "ג": "OH2", "ד": "H3O"}, "ans": "ב"},
    ]
}

DIFF_LABEL = {"easy": "🟢 קל", "medium": "🟡 בינוני", "hard": "🔴 קשה"}
DIFF_TIME  = {"easy": 30, "medium": 25, "hard": 20}
DIFF_PTS   = {"easy": (30,20,10), "medium": (50,30,20), "hard": (80,50,30)}

STORY_OPENERS = [
    "היה היה אדם שמצא מפה ישנה בעליית הגג...",
    "באחד הבקרים, כל הצבעים נעלמו מהעולם...",
    "הרובוט הראשון שקיבל רגשות החליט לפתוח קפה...",
    "הדלת שבחדר הסוד נפתחה בדיוק בחצות...",
    "הכבשה ה-13 לא הצליחה להירדם — היא ידעה משהו...",
]

# State
SCORES   = {}
trivia   = {}
tourn    = {}
tol      = {}
story    = {}
daily_chats = set()

def get_name(u): return u.first_name + (f" {u.last_name}" if u.last_name else "")

def s_add(cid, uid, name, pts, ok=False, bad=False):
    cid,uid = str(cid),str(uid)
    if cid not in SCORES: SCORES[cid]={}
    if uid not in SCORES[cid]: SCORES[cid][uid]={"name":name,"points":0,"correct":0,"wrong":0,"streak":0}
    p=SCORES[cid][uid]; p["points"]+=pts; p["name"]=name
    if ok: p["correct"]+=1; p["streak"]+=1
    if bad: p["wrong"]+=1; p["streak"]=0

def s_board(cid,n=10):
    cid=str(cid)
    if cid not in SCORES: return []
    return sorted([(v["name"],v["points"]) for v in SCORES[cid].values()],key=lambda x:x[1],reverse=True)[:n]

def s_stats(cid,uid):
    cid,uid=str(cid),str(uid)
    return SCORES.get(cid,{}).get(uid)

def after_menu():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("❓ שאלה נוספת", callback_data="m_another"),
        InlineKeyboardButton("🏆 ניקוד",       callback_data="m_scores"),
    ],[
        InlineKeyboardButton("🎯 טורניר",      callback_data="m_tournament"),
        InlineKeyboardButton("🎮 משחקים",      callback_data="m_games"),
    ]])

def diff_menu(action):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🟢 קל",    callback_data=f"d_{action}_easy"),
        InlineKeyboardButton("🟡 בינוני",callback_data=f"d_{action}_medium"),
        InlineKeyboardButton("🔴 קשה",   callback_data=f"d_{action}_hard"),
    ]])

def games_menu():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("❓ טריוויה",     callback_data="m_another"),
        InlineKeyboardButton("🤥 אמת/שקר",    callback_data="m_tol"),
    ],[
        InlineKeyboardButton("📖 סיפור",       callback_data="m_story"),
        InlineKeyboardButton("🏆 ניקוד",       callback_data="m_scores"),
    ]])

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎮 *GameBot המשודרג!*\n\n"
        "❓ /trivia — טריוויה עם רמות קושי\n"
        "🎯 /tournament — טורניר 10 שאלות\n"
        "🤥 /truthorlie — אמת או שקר\n"
        "📖 /story — סיפור קבוצתי\n"
        "🏆 /scores — טבלת מובילים\n"
        "📊 /mystats — הסטטיסטיקות שלי\n"
        "📅 /daily — שאלת יום אוטומטית\n"
        "🔄 /reset — אפס ניקוד (אדמין)",
        parse_mode="Markdown", reply_markup=games_menu()
    )

async def cb_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    cid = q.message.chat_id; d = q.data

    if d.startswith("d_"):
        _, action, diff = d.split("_")
        if action == "trivia":     await ask_trivia(ctx, cid, diff)
        elif action == "tournament": await start_tourn(ctx, cid, diff)

    elif d == "m_another":   await q.message.reply_text("בחרו רמת קושי:", reply_markup=diff_menu("trivia"))
    elif d == "m_tournament": await q.message.reply_text("בחרו רמת קושי לטורניר:", reply_markup=diff_menu("tournament"))
    elif d == "m_games":     await q.message.reply_text("בחרו משחק:", reply_markup=games_menu())
    elif d == "m_scores":
        board = s_board(cid)
        if not board: await q.message.reply_text("אין ניקוד עדיין!")
        else:
            medals=["🥇","🥈","🥉"]
            lines=["🏆 *טבלת המובילים*\n"]
            for i,(n,p) in enumerate(board): lines.append(f"{medals[i] if i<3 else f'{i+1}.'} {n} — *{p}* נק׳")
            await q.message.reply_text("\n".join(lines), parse_mode="Markdown")
    elif d == "m_tol":
        tol[cid]={"submissions":[],"votes":{},"active":True}
        await q.message.reply_text("🤥 *אמת או שקר התחיל!*\n\nכל אחד: `/tol_submit עובדה`\nאחר כך: `/tol_reveal`", parse_mode="Markdown")
    elif d == "m_story":
        opener=random.choice(STORY_OPENERS)
        story[cid]={"opener":opener,"entries":[],"last_user":None,"active":True}
        await q.message.reply_text(f"📖 *סיפור קבוצתי!*\n\n_{opener}_\n\n`/story_add המשפט שלכם`", parse_mode="Markdown")
    elif d.startswith("tol_"):
        await tol_vote_cb(update, ctx)

async def trivia_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("בחרו רמת קושי:", reply_markup=diff_menu("trivia"))

async def ask_trivia(ctx, cid, diff="medium"):
    if cid in trivia and trivia[cid].get("active"):
        await ctx.bot.send_message(cid,"❓ יש שאלה פעילה! ענו עליה קודם."); return
    q=random.choice(QUESTIONS[diff]); t=DIFF_TIME[diff]
    trivia[cid]={"q":q,"answered":{},"correct_count":0,"active":True,"diff":diff}
    opts="\n".join([f"{l}) {a}" for l,a in q["opts"].items()])
    pts=DIFF_PTS[diff][0]
    await ctx.bot.send_message(cid, f"{DIFF_LABEL[diff]} | ⏱ {t}שנ׳ | 🏅 עד {pts} נק׳\n\n❓ *{q['q']}*\n\n{opts}", parse_mode="Markdown")

    async def alerts():
        for secs, msg in [(10,"💨 עברו 10 שניות!"),(20,"⚡ עוד 10 שניות!"),(t-5,"😱 5 שניות אחרונות!!!")]:
            if secs < t:
                await asyncio.sleep(secs - (secs - secs))
        await asyncio.sleep(t - 5)
        if cid in trivia and trivia[cid].get("active"):
            await ctx.bot.send_message(cid,"😱 5 שניות אחרונות!!!")

    async def reveal():
        await asyncio.sleep(t)
        if cid in trivia and trivia[cid].get("active"):
            k=trivia[cid]["q"]["ans"]; v=trivia[cid]["q"]["opts"][k]
            trivia[cid]["active"]=False
            await ctx.bot.send_message(cid, f"⏰ הזמן עבר!\n✅ התשובה: *{k}) {v}*", parse_mode="Markdown", reply_markup=after_menu())

    asyncio.create_task(alerts())
    asyncio.create_task(reveal())

async def handle_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    if cid in tourn and tourn[cid].get("active"):
        await handle_tourn_answer(update, ctx); return
    if cid not in trivia or not trivia[cid].get("active"): return
    user=update.effective_user; uid=user.id; name=get_name(user)
    text=update.message.text.strip().upper()
    game=trivia[cid]
    if uid in game["answered"]: return
    game["answered"][uid]=text
    correct=game["q"]["ans"]; diff=game["diff"]
    if text==correct:
        cnt=game["correct_count"]
        pts=DIFF_PTS[diff][0] if cnt==0 else DIFF_PTS[diff][1] if cnt==1 else DIFF_PTS[diff][2]
        game["correct_count"]+=1
        s_add(cid,uid,name,pts,ok=True)
        ans_text=game["q"]["opts"][correct]
        st=SCORES[str(cid)][str(uid)]["streak"]
        streak_msg=f"\n🔥 רצף של {st}!" if st>=3 else ""
        game["active"]=False
        await update.message.reply_text(f"✅ נכון, {name}! +{pts} נק׳ 🎉\nתשובה: *{correct}) {ans_text}*{streak_msg}", parse_mode="Markdown", reply_markup=after_menu())
    else:
        s_add(cid,uid,name,0,bad=True)
        await update.message.reply_text(f"❌ לא נכון, {name}!")

async def tournament_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("בחרו רמת קושי לטורניר:", reply_markup=diff_menu("tournament"))

async def start_tourn(ctx, cid, diff):
    if cid in tourn and tourn[cid].get("active"):
        await ctx.bot.send_message(cid,"🎯 טורניר כבר פעיל!"); return
    qs=random.sample(QUESTIONS[diff], min(10,len(QUESTIONS[diff])))
    tourn[cid]={"active":True,"diff":diff,"qs":qs,"cur":0,"round_scores":{},"answered":set()}
    await ctx.bot.send_message(cid, f"🎯 *טורניר התחיל!* {DIFF_LABEL[diff]}\n10 שאלות — מי יצבור הכי הרבה?", parse_mode="Markdown")
    await send_tourn_q(ctx, cid)

async def send_tourn_q(ctx, cid):
    t=tourn[cid]
    if t["cur"]>=len(t["qs"]): await end_tourn(ctx,cid); return
    q=t["qs"][t["cur"]]; t["answered"]=set()
    n=t["cur"]+1; total=len(t["qs"]); diff=t["diff"]
    opts="\n".join([f"{l}) {a}" for l,a in q["opts"].items()])
    await ctx.bot.send_message(cid, f"🎯 שאלה {n}/{total} | {DIFF_LABEL[diff]}\n\n❓ *{q['q']}*\n\n{opts}", parse_mode="Markdown")
    cur=t["cur"]
    async def timeout():
        await asyncio.sleep(DIFF_TIME[diff])
        if cid in tourn and tourn[cid].get("active") and tourn[cid]["cur"]==cur:
            k=q["ans"]; v=q["opts"][k]
            tourn[cid]["cur"]+=1
            await ctx.bot.send_message(cid, f"⏰ הזמן עבר! תשובה: *{k}) {v}*", parse_mode="Markdown")
            await asyncio.sleep(2); await send_tourn_q(ctx,cid)
    asyncio.create_task(timeout())

async def handle_tourn_answer(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cid=update.effective_chat.id; user=update.effective_user
    uid=user.id; name=get_name(user); t=tourn[cid]
    if uid in t["answered"]: return
    text=update.message.text.strip().upper()
    q=t["qs"][t["cur"]]; correct=q["ans"]; diff=t["diff"]
    if text==correct:
        cnt=len(t["answered"])
        pts=DIFF_PTS[diff][0] if cnt==0 else DIFF_PTS[diff][1] if cnt==1 else DIFF_PTS[diff][2]
        t["answered"].add(uid)
        if uid not in t["round_scores"]: t["round_scores"][uid]={"name":name,"pts":0}
        t["round_scores"][uid]["pts"]+=pts; t["round_scores"][uid]["name"]=name
        s_add(cid,uid,name,pts,ok=True)
        ans_text=q["opts"][correct]; t["cur"]+=1
        await update.message.reply_text(f"✅ {name} +{pts} נק׳! תשובה: *{correct}) {ans_text}*", parse_mode="Markdown")
        await asyncio.sleep(2); await send_tourn_q(ctx,cid)
    else:
        t["answered"].add(uid); s_add(cid,uid,name,0,bad=True)
        await update.message.reply_text(f"❌ לא נכון {name}!")

async def end_tourn(ctx, cid):
    t=tourn[cid]; t["active"]=False
    board=sorted(t["round_scores"].items(),key=lambda x:x[1]["pts"],reverse=True)
    medals=["🥇","🥈","🥉"]; lines=["🎯 *הטורניר הסתיים!*\n"]
    for i,(uid,d) in enumerate(board): lines.append(f"{medals[i] if i<3 else f'{i+1}.'} {d['name']} — {d['pts']} נק׳")
    if board: lines.append(f"\n👑 המנצח: *{board[0][1]['name']}*!")
    await ctx.bot.send_message(cid,"\n".join(lines),parse_mode="Markdown",reply_markup=after_menu())

async def scores_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    board=s_board(update.effective_chat.id)
    if not board: await update.message.reply_text("אין ניקוד! 😄"); return
    medals=["🥇","🥈","🥉"]; lines=["🏆 *טבלת המובילים*\n"]
    for i,(n,p) in enumerate(board): lines.append(f"{medals[i] if i<3 else f'{i+1}.'} {n} — *{p}* נק׳")
    await update.message.reply_text("\n".join(lines),parse_mode="Markdown",reply_markup=after_menu())

async def mystats_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user=update.effective_user; stats=s_stats(update.effective_chat.id,user.id)
    if not stats: await update.message.reply_text("אין סטטיסטיקות עדיין! 🎮"); return
    total=stats["correct"]+stats["wrong"]
    pct=int(stats["correct"]/total*100) if total>0 else 0
    bar="🟩"*(pct//10)+"⬜"*(10-pct//10)
    await update.message.reply_text(
        f"📊 *הסטטיסטיקות של {stats['name']}*\n\n"
        f"🏅 ניקוד: *{stats['points']}* נק׳\n"
        f"✅ נכון: {stats['correct']}\n"
        f"❌ שגוי: {stats['wrong']}\n"
        f"🎯 הצלחה: {pct}%\n{bar}\n"
        f"🔥 רצף: {stats['streak']}",
        parse_mode="Markdown"
    )

async def reset_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cid=update.effective_chat.id
    m=await ctx.bot.get_chat_member(cid,update.effective_user.id)
    if m.status not in ("administrator","creator"):
        await update.message.reply_text("❌ רק אדמין!"); return
    SCORES[str(cid)]={}; await update.message.reply_text("✅ הניקוד אופס!")

async def daily_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cid=update.effective_chat.id
    if cid in daily_chats:
        daily_chats.discard(cid); await update.message.reply_text("📅 שאלת היום הושבתה.")
    else:
        daily_chats.add(cid); await update.message.reply_text("📅 *שאלת יום הופעלה!*\nכל יום ב-10:00 תגיע שאלה אוטומטית 🎉", parse_mode="Markdown")

async def send_daily(ctx: ContextTypes.DEFAULT_TYPE):
    for cid in list(daily_chats):
        try:
            diff=random.choice(["easy","medium","hard"])
            await ctx.bot.send_message(cid,f"📅 *שאלת היום!* {DIFF_LABEL[diff]}",parse_mode="Markdown")
            await ask_trivia(ctx,cid,diff)
        except Exception as e: print(f"daily error {cid}: {e}")

async def tol_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cid=update.effective_chat.id
    tol[cid]={"submissions":[],"votes":{},"active":True}
    await update.message.reply_text("🤥 *אמת או שקר!*\n\nכל אחד: `/tol_submit עובדה`\nחשיפה: `/tol_reveal`", parse_mode="Markdown")

async def tol_submit(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cid=update.effective_chat.id
    if cid not in tol or not tol[cid]["active"]:
        await update.message.reply_text("אין משחק. /truthorlie להתחלה"); return
    if not ctx.args: await update.message.reply_text("כתוב: `/tol_submit עובדה`",parse_mode="Markdown"); return
    user=update.effective_user; name=get_name(user)
    tol[cid]["submissions"].append((user.id,name," ".join(ctx.args),random.choice([True,False])))
    await update.message.reply_text(f"✅ {name} נשמר! 🤫")

async def tol_reveal(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cid=update.effective_chat.id
    if cid not in tol or not tol[cid]["active"]: await update.message.reply_text("אין משחק."); return
    subs=tol[cid]["submissions"]
    if len(subs)<2: await update.message.reply_text("צריך לפחות 2 שחקנים!"); return
    for i,(uid,name,text,is_truth) in enumerate(subs):
        kb=[[InlineKeyboardButton("✅ אמת",callback_data=f"tol_{i}_true_{uid}"),
             InlineKeyboardButton("❌ שקר",callback_data=f"tol_{i}_false_{uid}")]]
        await ctx.bot.send_message(cid,f"🤔 *עובדה #{i+1}* (מאת: {name})\n\n_{text}_",
                                   reply_markup=InlineKeyboardMarkup(kb),parse_mode="Markdown")

async def tol_vote_cb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    cid=q.message.chat_id
    if cid not in tol: return
    data=q.data.split("_"); idx,vote,sid=int(data[1]),data[2],int(data[3])
    voter=q.from_user; vname=get_name(voter)
    if voter.id==sid: await q.answer("לא יכול להצביע על עצמך! 😄",show_alert=True); return
    key=(voter.id,idx)
    if key in tol[cid]["votes"]: await q.answer("כבר הצבעת!",show_alert=True); return
    tol[cid]["votes"][key]=(vote,vname)
    if len([k for k in tol[cid]["votes"] if k[1]==idx])>=3:
        is_truth=tol[cid]["submissions"][idx][3]; correct="true" if is_truth else "false"
        ans_text="אמת ✅" if is_truth else "שקר ❌"; winners=[]
        for (vid,i),(ans,vn) in tol[cid]["votes"].items():
            if i==idx and ans==correct and vid!=sid:
                s_add(cid,vid,vn,20,ok=True); winners.append(vn)
        await q.edit_message_text(f"{q.message.text}\n\n🎯 *התשובה: {ans_text}*\nניחשו נכון: {', '.join(winners) or 'אף אחד'} (+20 נק׳)",parse_mode="Markdown")

async def story_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cid=update.effective_chat.id; opener=random.choice(STORY_OPENERS)
    story[cid]={"opener":opener,"entries":[],"last_user":None,"active":True}
    await update.message.reply_text(f"📖 *סיפור קבוצתי!*\n\n_{opener}_\n\n`/story_add המשפט שלכם`\n/story_read | /story_end",parse_mode="Markdown")

async def story_add(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cid=update.effective_chat.id
    if cid not in story or not story[cid]["active"]: await update.message.reply_text("אין סיפור. /story"); return
    if not ctx.args: await update.message.reply_text("כתוב: `/story_add משפט`",parse_mode="Markdown"); return
    user=update.effective_user; name=get_name(user)
    if story[cid]["last_user"]==user.id: await update.message.reply_text("⏳ תן לאחרים קודם! 😄"); return
    text=" ".join(ctx.args); story[cid]["entries"].append((user.id,name,text)); story[cid]["last_user"]=user.id
    s_add(cid,user.id,name,10,ok=True); count=len(story[cid]["entries"])
    extra=f"\n\n🎲 _וואו {count} משפטים!_" if count%5==0 else ""
    await update.message.reply_text(f"✍️ {name}: _{text}_ +10 נק׳{extra}",parse_mode="Markdown")

async def story_read(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cid=update.effective_chat.id
    if cid not in story: await update.message.reply_text("אין סיפור."); return
    parts=[story[cid]["opener"]]+[t for _,_,t in story[cid]["entries"]]
    await update.message.reply_text(f"📖 *הסיפור:*\n\n_{' '.join(parts)}_",parse_mode="Markdown")

async def story_end(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cid=update.effective_chat.id
    if cid not in story: await update.message.reply_text("אין סיפור."); return
    parts=[story[cid]["opener"]]+[t for _,_,t in story[cid]["entries"]]
    story[cid]["active"]=False
    await update.message.reply_text(f"📖 *הסיפור הושלם! 🎉*\n\n_{' '.join(parts)}_\n\n{len(story[cid]['entries'])} משפטים!",parse_mode="Markdown",reply_markup=games_menu())

def main():
    app=Application.builder().token(TOKEN).build()
    app.job_queue.run_daily(send_daily,time=dtime(hour=10,minute=0))
    app.add_handler(CommandHandler("start",start))
    app.add_handler(CommandHandler("scores",scores_cmd))
    app.add_handler(CommandHandler("mystats",mystats_cmd))
    app.add_handler(CommandHandler("reset",reset_cmd))
    app.add_handler(CommandHandler("trivia",trivia_cmd))
    app.add_handler(CommandHandler("tournament",tournament_cmd))
    app.add_handler(CommandHandler("daily",daily_cmd))
    app.add_handler(CommandHandler("truthorlie",tol_cmd))
    app.add_handler(CommandHandler("tol_submit",tol_submit))
    app.add_handler(CommandHandler("tol_reveal",tol_reveal))
    app.add_handler(CommandHandler("story",story_cmd))
    app.add_handler(CommandHandler("story_add",story_add))
    app.add_handler(CommandHandler("story_read",story_read))
    app.add_handler(CommandHandler("story_end",story_end))
    app.add_handler(CallbackQueryHandler(cb_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("🤖 GameBot המשודרג רץ!")
    app.run_polling()

if __name__=="__main__":
    main()
