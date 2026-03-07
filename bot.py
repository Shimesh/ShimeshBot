import os, random, asyncio, re, html, json
from datetime import time as dtime
import urllib.request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes
)

TOKEN   = os.environ.get("BOT_TOKEN", "")
# Public proxy APIs - work from any IP worldwide
TZEVA_ADOM_URL  = "https://api.tzevaadom.co.il/notifications"  # real-time active alerts
TZEVA_HISTORY   = "https://api.tzevaadom.co.il/notifications"
OREF_PROXY_URL  = "https://red-alert-proxy.vercel.app/api/alerts"  # fallback proxy

# ── State ─────────────────────────────────────────────────────────────────────
SCORES       = {}
trivia       = {}
tourn        = {}
tol          = {}
story        = {}
seen_ids     = set()
chat_members = {}   # chat_id -> set of user_ids

# ── Helpers ───────────────────────────────────────────────────────────────────
def get_name(u): return u.first_name + (f" {u.last_name}" if u.last_name else "")

def track(cid, uid):
    if cid not in chat_members: chat_members[cid] = set()
    chat_members[cid].add(uid)

def s_add(cid, uid, name, pts, ok=False, bad=False):
    cid,uid = str(cid),str(uid)
    if cid not in SCORES: SCORES[cid]={}
    if uid not in SCORES[cid]: SCORES[cid][uid]={"name":name,"points":0,"correct":0,"wrong":0,"streak":0}
    p=SCORES[cid][uid]; p["points"]+=pts; p["name"]=name
    if ok:  p["correct"]+=1; p["streak"]+=1
    if bad: p["wrong"]+=1;   p["streak"]=0

def s_board(cid, n=10):
    cid=str(cid)
    if cid not in SCORES: return []
    return sorted([(v["name"],v["points"]) for v in SCORES[cid].values()],key=lambda x:x[1],reverse=True)[:n]

def s_stats(cid, uid):
    return SCORES.get(str(cid),{}).get(str(uid))

# ── Alert logic ───────────────────────────────────────────────────────────────
AD_KEYWORDS = [
    "פרסום","מודעה","שיתוף פעולה","ספונסר","קידום","מבצע","הנחה",
    "קנה","מכירה","להזמין","לרכוש","לקנות","ביטוח","השקעה","קריפטו",
    "שלחו הודעה","צרו קשר","contact","whatsapp","sponsor","affiliate","promo"
]

ALERT_KEYWORDS = [
    "שיגור","ירי","טיל","רקטה","אזעקה","כיפת ברזל","יירוט",
    "חיזבאללה","חמאס","עזה","לבנון","תימן","עיראק","איראן",
    "כוננות","פגיעה","נפילה","התרעה","סיכול","צבע אדום"
]

def is_ad(text): return any(k.lower() in text.lower() for k in AD_KEYWORDS)
def is_alert(text): return any(k in text for k in ALERT_KEYWORDS)

def fetch_active_alerts():
    """Fetch live alerts - tries multiple public proxies"""
    urls = [
        ("tzevaadom", TZEVA_ADOM_URL),
        ("proxy",     OREF_PROXY_URL),
    ]
    for name, url in urls:
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json",
            })
            with urllib.request.urlopen(req, timeout=6) as r:
                raw = r.read().decode("utf-8-sig").strip()
                if not raw or raw in ("null","[]","{}"): return []
                data = json.loads(raw)
                # tzevaadom returns {"notifications": [...]}
                if isinstance(data, dict):
                    cities = data.get("notifications", data.get("data", []))
                elif isinstance(data, list):
                    cities = data
                else:
                    cities = []
                if cities:
                    print(f"✅ Alerts from {name}: {cities}")
                    return cities
        except Exception as e:
            print(f"Alert fetch {name} error: {e}")
    return []

# Track last sent alert to avoid duplicates
last_alert_hash = {"val": ""}

async def check_alerts(ctx: ContextTypes.DEFAULT_TYPE):
    if not chat_members: return
    try:
        cities = fetch_active_alerts()
        if not cities: return

        # Build a hash to avoid re-sending same alert
        alert_hash = str(sorted(str(c) for c in cities))
        if alert_hash == last_alert_hash["val"]: return
        last_alert_hash["val"] = alert_hash

        # Format cities list
        if isinstance(cities[0], dict):
            city_names = [c.get("name", c.get("city", str(c))) for c in cities]
        else:
            city_names = [str(c) for c in cities]

        cities_text = "\n".join(f"• {c}" for c in city_names[:25])
        msg = (
            "🚨 *אזעקת צבע אדום!*\n\n"
            f"*אזורים מותרעים:*\n{cities_text}\n\n"
            "⚠️ *היכנסו למרחב המוגן מיד!*\n"
            "_מקור: פיקוד העורף_"
        )
        for cid in list(chat_members.keys()):
            try:
                await ctx.bot.send_message(cid, msg, parse_mode="Markdown")
            except Exception as e:
                print(f"Alert send error {cid}: {e}")
    except Exception as e:
        print(f"check_alerts error: {e}")

# ── Questions ─────────────────────────────────────────────────────────────────
QUESTIONS = {
    "easy": [
        {"q":"כמה גרמים יש בקילוגרם?","opts":{"א":"100","ב":"500","ג":"1000","ד":"2000"},"ans":"ג"},
        {"q":"כמה צלעות יש למשולש?","opts":{"א":"2","ב":"3","ג":"4","ד":"5"},"ans":"ב"},
        {"q":"כמה שעות יש ביום?","opts":{"א":"12","ב":"24","ג":"48","ד":"36"},"ans":"ב"},
        {"q":"כמה רגליים יש לעכביש?","opts":{"א":"4","ב":"6","ג":"8","ד":"10"},"ans":"ג"},
        {"q":"מה הוא היונק הגדול ביותר?","opts":{"א":"פיל","ב":"לוויתן כחול","ג":"ג׳ירפה","ד":"היפופוטם"},"ans":"ב"},
        {"q":"איזה צבע מתקבל מערבוב אדום וכחול?","opts":{"א":"ירוק","ב":"כתום","ג":"סגול","ד":"חום"},"ans":"ג"},
        {"q":"כמה ימים יש בשבוע?","opts":{"א":"5","ב":"6","ג":"7","ד":"8"},"ans":"ג"},
        {"q":"כמה חודשים יש בשנה?","opts":{"א":"10","ב":"11","ג":"12","ד":"13"},"ans":"ג"},
        {"q":"מה הצבע של עלים?","opts":{"א":"אדום","ב":"כחול","ג":"ירוק","ד":"צהוב"},"ans":"ג"},
        {"q":"מה הוא הים הגדול ביותר?","opts":{"א":"אטלנטי","ב":"הודי","ג":"ארקטי","ד":"האוקיינוס השקט"},"ans":"ד"},
    ],
    "medium": [
        {"q":"מהי הבירה של אוסטרליה?","opts":{"א":"סידני","ב":"קנברה","ג":"מלבורן","ד":"פרת׳"},"ans":"ב"},
        {"q":"מי צייר את המונה ליזה?","opts":{"א":"מיכלאנג׳לו","ב":"רפאל","ג":"לאונרדו דה וינצ׳י","ד":"פיקאסו"},"ans":"ג"},
        {"q":"מהו כוכב הלכת הגדול ביותר?","opts":{"א":"שבתאי","ב":"צדק","ג":"אורנוס","ד":"נפטון"},"ans":"ב"},
        {"q":"באיזו שנה הוקמה ישראל?","opts":{"א":"1945","ב":"1947","ג":"1948","ד":"1950"},"ans":"ג"},
        {"q":"הסימול הכימי של זהב?","opts":{"א":"Ag","ב":"Al","ג":"Au","ד":"Cu"},"ans":"ג"},
        {"q":"הנהר הארוך ביותר?","opts":{"א":"האמזונס","ב":"הנילוס","ג":"המיסיסיפי","ד":"היאנגצה"},"ans":"ב"},
        {"q":"מי כתב רומיאו ויוליה?","opts":{"א":"דיקנס","ב":"שקספיר","ג":"מולייר","ד":"גתה"},"ans":"ב"},
        {"q":"המדינה הגדולה ביותר?","opts":{"א":"קנדה","ב":"סין","ג":"ארצות הברית","ד":"רוסיה"},"ans":"ד"},
        {"q":"כמה שניות יש בשעה?","opts":{"א":"360","ב":"3600","ג":"36000","ד":"600"},"ans":"ב"},
        {"q":"עיר הבירה של ברזיל?","opts":{"א":"ריו","ב":"סאו פאולו","ג":"ברזיליה","ד":"סלבדור"},"ans":"ג"},
    ],
    "hard": [
        {"q":"המספר הראשוני ה-10?","opts":{"א":"23","ב":"27","ג":"29","ד":"31"},"ans":"ג"},
        {"q":"מי פיתח את תורת הקוואנטים?","opts":{"א":"איינשטיין","ב":"בוהר","ג":"מקס פלאנק","ד":"שרדינגר"},"ans":"ג"},
        {"q":"בירת קזחסטן?","opts":{"א":"אלמא-אטה","ב":"אסטנה","ג":"טשקנט","ד":"בישקק"},"ans":"ב"},
        {"q":"כמה עצמות בגוף האדם?","opts":{"א":"186","ב":"196","ג":"206","ד":"216"},"ans":"ג"},
        {"q":"המרחק לשמש במיליון ק״מ?","opts":{"א":"100","ב":"150","ג":"200","ד":"250"},"ans":"ב"},
        {"q":"מתי הושלם הכולוסיאום?","opts":{"א":"70 לספירה","ב":"80 לספירה","ג":"90 לספירה","ד":"100 לספירה"},"ans":"ב"},
        {"q":"שפת התכנות של גוידו ון רוסום?","opts":{"א":"Java","ב":"Ruby","ג":"Python","ד":"Perl"},"ans":"ג"},
        {"q":"כמה לוויינים למאדים?","opts":{"א":"0","ב":"1","ג":"2","ד":"3"},"ans":"ג"},
        {"q":"מי כתב ״מלחמה ושלום״?","opts":{"א":"דוסטויבסקי","ב":"צ׳כוב","ג":"טורגנייב","ד":"טולסטוי"},"ans":"ד"},
        {"q":"הצפד הכימי של מים?","opts":{"א":"HO","ב":"H2O","ג":"OH2","ד":"H3O"},"ans":"ב"},
    ]
}

DIFF_LABEL={"easy":"🟢 קל","medium":"🟡 בינוני","hard":"🔴 קשה"}
DIFF_TIME ={"easy":30,"medium":25,"hard":20}
DIFF_PTS  ={"easy":(30,20,10),"medium":(50,30,20),"hard":(80,50,30)}

STORY_OPENERS=[
    "היה היה אדם שמצא מפה ישנה בעליית הגג...",
    "באחד הבקרים, כל הצבעים נעלמו מהעולם...",
    "הרובוט הראשון שקיבל רגשות החליט לפתוח קפה...",
    "הדלת שבחדר הסוד נפתחה בדיוק בחצות...",
    "הכבשה ה-13 לא הצליחה להירדם — היא ידעה משהו...",
]

# ── Keyboards ─────────────────────────────────────────────────────────────────
def after_menu():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("❓ שאלה נוספת",callback_data="m_another"),
        InlineKeyboardButton("🏆 ניקוד",      callback_data="m_scores"),
    ],[
        InlineKeyboardButton("🎯 טורניר",     callback_data="m_tournament"),
        InlineKeyboardButton("🎮 משחקים",     callback_data="m_games"),
    ]])

def diff_menu(action):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🟢 קל +30",    callback_data=f"d_{action}_easy"),
        InlineKeyboardButton("🟡 בינוני +50",callback_data=f"d_{action}_medium"),
        InlineKeyboardButton("🔴 קשה +80",   callback_data=f"d_{action}_hard"),
    ]])

def games_menu():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("❓ טריוויה", callback_data="m_another"),
        InlineKeyboardButton("🤥 אמת/שקר",callback_data="m_tol"),
    ],[
        InlineKeyboardButton("📖 סיפור",   callback_data="m_story"),
        InlineKeyboardButton("🏆 ניקוד",   callback_data="m_scores"),
    ],[
        InlineKeyboardButton("📊 הסטטיסטיקות שלי",callback_data="m_mystats"),
        InlineKeyboardButton("🎯 טורניר", callback_data="m_tournament"),
    ]])

def tol_menu(): return InlineKeyboardMarkup([[InlineKeyboardButton("✍️ שלח עובדה",callback_data="tol_prompt"),InlineKeyboardButton("👁 חשוף הכל",callback_data="tol_do_reveal")]])
def story_kb(): return InlineKeyboardMarkup([[InlineKeyboardButton("✍️ הוסף",callback_data="story_prompt"),InlineKeyboardButton("📖 קרא",callback_data="story_read_cb"),InlineKeyboardButton("🏁 סיים",callback_data="story_end_cb")]])

# ── /start — onboarding ───────────────────────────────────────────────────────
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cid=update.effective_chat.id; uid=update.effective_user.id
    track(cid,uid)
    await update.message.reply_text(
        "👋 *שלום וברוכים הבאים!*\n\n"
        "אני בוט קבוצתי עם שני מצבים:\n\n"
        "🚨 *התרעות שיגורים אוטומטיות*\n"
        "עוקב אחרי מקורות ביטחוניים בזמן אמת, מסנן פרסומות, ומצליב עם פיקוד העורף.\n"
        "ההתרעות מגיעות *אוטומטית* — אין צורך להפעיל כלום.\n\n"
        "🎮 *משחקים קבוצתיים*\n"
        "טריוויה עם רמות קושי, טורניר, אמת/שקר, סיפור קבוצתי.\n"
        "כולם מתחרים על טבלת המובילים!\n\n"
        "━━━━━━━━━━━━━━━\n"
        "👇 בחרו במה להתחיל:",
        parse_mode="Markdown", reply_markup=games_menu()
    )

async def new_member(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cid=update.effective_chat.id
    for member in update.message.new_chat_members:
        if member.is_bot: continue
        track(cid, member.id)
        await update.message.reply_text(
            f"👋 ברוך הבא *{get_name(member)}*!\n\n"
            f"אני בוט עם משחקים קבוצתיים 🎮 והתרעות שיגורים אוטומטיות 🚨\n\n"
            f"לחץ /start לפרטים, או בחר ישר:",
            parse_mode="Markdown", reply_markup=games_menu()
        )

# ── Callbacks ─────────────────────────────────────────────────────────────────
async def cb_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    cid=q.message.chat_id; uid=q.from_user.id; d=q.data; name=get_name(q.from_user)
    track(cid,uid)

    if d.startswith("d_"):
        _,action,diff=d.split("_")
        if action=="trivia":      await ask_trivia(ctx,cid,diff)
        elif action=="tournament": await start_tourn(ctx,cid,diff)
    elif d=="m_another":    await q.message.reply_text("בחרו רמת קושי:",reply_markup=diff_menu("trivia"))
    elif d=="m_tournament": await q.message.reply_text("בחרו רמת קושי לטורניר:",reply_markup=diff_menu("tournament"))
    elif d=="m_games":      await q.message.reply_text("בחרו משחק:",reply_markup=games_menu())
    elif d=="m_scores":
        board=s_board(cid)
        if not board: await q.message.reply_text("אין ניקוד עדיין!")
        else:
            medals=["🥇","🥈","🥉"]; lines=["🏆 *טבלת המובילים*\n"]
            for i,(n,p) in enumerate(board): lines.append(f"{medals[i] if i<3 else f'{i+1}.'} {n} — *{p}* נק׳")
            await q.message.reply_text("\n".join(lines),parse_mode="Markdown")
    elif d=="m_mystats":
        stats=s_stats(cid,uid)
        if not stats: await q.message.reply_text(f"אין סטטיסטיקות עדיין {name}! שחק קצת 🎮"); return
        total=stats["correct"]+stats["wrong"]; pct=int(stats["correct"]/total*100) if total>0 else 0
        bar="🟩"*(pct//10)+"⬜"*(10-pct//10)
        await q.message.reply_text(f"📊 *{stats['name']}*\n🏅 {stats['points']} נק׳\n✅ {stats['correct']} נכון | ❌ {stats['wrong']} שגוי\n🎯 {pct}%\n{bar}\n🔥 רצף: {stats['streak']}",parse_mode="Markdown")
    elif d=="m_tol":
        tol[cid]={"submissions":[],"votes":{},"active":True}
        await q.message.reply_text("🤥 *אמת או שקר!*\nלחצו ׳שלח עובדה׳ — כל אחד בתורו:",parse_mode="Markdown",reply_markup=tol_menu())
    elif d=="m_story":
        opener=random.choice(STORY_OPENERS)
        story[cid]={"opener":opener,"entries":[],"last_user":None,"active":True}
        await q.message.reply_text(f"📖 *סיפור קבוצתי!*\n\n_{opener}_\n\nלחצו ׳הוסף׳:",parse_mode="Markdown",reply_markup=story_kb())
    elif d=="tol_prompt":
        await q.message.reply_text(f"✍️ *{name}*, כתב את העובדה שלך:",parse_mode="Markdown")
        ctx.user_data["awaiting_tol"]=cid
    elif d=="tol_do_reveal":
        await do_tol_reveal(ctx,cid)
    elif d=="story_prompt":
        await q.message.reply_text(f"✍️ *{name}*, כתב את המשפט שלך:",parse_mode="Markdown")
        ctx.user_data["awaiting_story"]=cid
    elif d=="story_read_cb":
        if cid not in story: await q.message.reply_text("אין סיפור פעיל."); return
        parts=[story[cid]["opener"]]+[t for _,_,t in story[cid]["entries"]]
        await q.message.reply_text(f"📖 *הסיפור:*\n\n_{' '.join(parts)}_",parse_mode="Markdown")
    elif d=="story_end_cb":
        if cid not in story: return
        parts=[story[cid]["opener"]]+[t for _,_,t in story[cid]["entries"]]
        story[cid]["active"]=False
        await q.message.reply_text(f"📖 *הסיפור הושלם! 🎉*\n\n_{' '.join(parts)}_\n\n{len(story[cid]['entries'])} משפטים!",parse_mode="Markdown",reply_markup=games_menu())
    elif d.startswith("tol_"):
        await tol_vote_cb(update,ctx)

# ── Trivia ────────────────────────────────────────────────────────────────────
async def trivia_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    track(update.effective_chat.id, update.effective_user.id)
    await update.message.reply_text("בחרו רמת קושי:",reply_markup=diff_menu("trivia"))

async def ask_trivia(ctx, cid, diff="medium"):
    if cid in trivia and trivia[cid].get("active"):
        await ctx.bot.send_message(cid,"❓ יש שאלה פעילה כבר!"); return
    q=random.choice(QUESTIONS[diff]); t=DIFF_TIME[diff]
    trivia[cid]={"q":q,"answered":{},"correct_count":0,"active":True,"diff":diff}
    kb=InlineKeyboardMarkup([[InlineKeyboardButton(f"{l}) {a}",callback_data=f"ans_{l}_{cid}")] for l,a in q["opts"].items()])
    pts=DIFF_PTS[diff][0]
    await ctx.bot.send_message(cid,f"{DIFF_LABEL[diff]} | ⏱ {t}שנ׳ | 🏅 עד {pts} נק׳\n\n❓ *{q['q']}*",parse_mode="Markdown",reply_markup=kb)
    async def warn():
        await asyncio.sleep(max(t-5,1))
        if cid in trivia and trivia[cid].get("active"):
            await ctx.bot.send_message(cid,"😱 5 שניות אחרונות!!!")
    async def reveal():
        await asyncio.sleep(t)
        if cid in trivia and trivia[cid].get("active"):
            k=trivia[cid]["q"]["ans"]; v=trivia[cid]["q"]["opts"][k]
            trivia[cid]["active"]=False
            await ctx.bot.send_message(cid,f"⏰ הזמן עבר!\n✅ התשובה: *{k}) {v}*",parse_mode="Markdown",reply_markup=after_menu())
    asyncio.create_task(warn()); asyncio.create_task(reveal())

async def ans_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query
    parts=q.data.split("_"); letter=parts[1]; cid=int(parts[2])
    if cid not in trivia or not trivia[cid].get("active"):
        await q.answer("השאלה כבר לא פעילה ⏰",show_alert=True); return
    user=q.from_user; uid=user.id; name=get_name(user); game=trivia[cid]
    if uid in game["answered"]: await q.answer("כבר ענית! ⏳",show_alert=True); return
    await q.answer()
    game["answered"][uid]=letter; correct=game["q"]["ans"]; diff=game["diff"]
    if letter==correct:
        cnt=game["correct_count"]
        pts=DIFF_PTS[diff][0] if cnt==0 else DIFF_PTS[diff][1] if cnt==1 else DIFF_PTS[diff][2]
        game["correct_count"]+=1; s_add(cid,uid,name,pts,ok=True)
        ans_text=game["q"]["opts"][correct]
        st=SCORES[str(cid)][str(uid)]["streak"]
        streak_msg=f"\n🔥 רצף של {st}!" if st>=3 else ""
        game["active"]=False
        await q.message.reply_text(f"✅ נכון, *{name}*! +{pts} נק׳ 🎉\nתשובה: *{correct}) {ans_text}*{streak_msg}",parse_mode="Markdown",reply_markup=after_menu())
    else:
        s_add(cid,uid,name,0,bad=True)
        await q.answer("❌ לא נכון! נסו שוב",show_alert=True)

# ── Tournament ────────────────────────────────────────────────────────────────
async def tournament_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    track(update.effective_chat.id, update.effective_user.id)
    await update.message.reply_text("בחרו רמת קושי לטורניר:",reply_markup=diff_menu("tournament"))

async def start_tourn(ctx, cid, diff):
    if cid in tourn and tourn[cid].get("active"):
        await ctx.bot.send_message(cid,"🎯 טורניר כבר פעיל!"); return
    qs=random.sample(QUESTIONS[diff],min(10,len(QUESTIONS[diff])))
    tourn[cid]={"active":True,"diff":diff,"qs":qs,"cur":0,"round_scores":{},"answered":set()}
    await ctx.bot.send_message(cid,f"🎯 *טורניר התחיל!* {DIFF_LABEL[diff]}\n10 שאלות — מי יצבור הכי הרבה?",parse_mode="Markdown")
    await send_tourn_q(ctx,cid)

async def send_tourn_q(ctx, cid):
    t=tourn[cid]
    if t["cur"]>=len(t["qs"]): await end_tourn(ctx,cid); return
    q=t["qs"][t["cur"]]; t["answered"]=set(); n=t["cur"]+1; total=len(t["qs"]); diff=t["diff"]
    kb=InlineKeyboardMarkup([[InlineKeyboardButton(f"{l}) {a}",callback_data=f"tans_{l}_{cid}")] for l,a in q["opts"].items()])
    await ctx.bot.send_message(cid,f"🎯 שאלה {n}/{total} | {DIFF_LABEL[diff]}\n\n❓ *{q['q']}*",parse_mode="Markdown",reply_markup=kb)
    cur=t["cur"]
    async def timeout():
        await asyncio.sleep(DIFF_TIME[diff])
        if cid in tourn and tourn[cid].get("active") and tourn[cid]["cur"]==cur:
            k=q["ans"]; v=q["opts"][k]; tourn[cid]["cur"]+=1
            await ctx.bot.send_message(cid,f"⏰ הזמן עבר! תשובה: *{k}) {v}*",parse_mode="Markdown")
            await asyncio.sleep(2); await send_tourn_q(ctx,cid)
    asyncio.create_task(timeout())

async def tans_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query
    parts=q.data.split("_"); letter=parts[1]; cid=int(parts[2])
    if cid not in tourn or not tourn[cid].get("active"):
        await q.answer("הטורניר כבר לא פעיל ⏰",show_alert=True); return
    user=q.from_user; uid=user.id; name=get_name(user); t=tourn[cid]
    if uid in t["answered"]: await q.answer("כבר ענית!",show_alert=True); return
    await q.answer()
    correct=t["qs"][t["cur"]]["ans"]; diff=t["diff"]
    if letter==correct:
        cnt=len(t["answered"]); pts=DIFF_PTS[diff][0] if cnt==0 else DIFF_PTS[diff][1] if cnt==1 else DIFF_PTS[diff][2]
        t["answered"].add(uid)
        if uid not in t["round_scores"]: t["round_scores"][uid]={"name":name,"pts":0}
        t["round_scores"][uid]["pts"]+=pts; t["round_scores"][uid]["name"]=name
        s_add(cid,uid,name,pts,ok=True); ans_text=t["qs"][t["cur"]]["opts"][correct]; t["cur"]+=1
        await q.message.reply_text(f"✅ *{name}* +{pts} נק׳! תשובה: *{correct}) {ans_text}*",parse_mode="Markdown")
        await asyncio.sleep(2); await send_tourn_q(ctx,cid)
    else:
        t["answered"].add(uid); s_add(cid,uid,name,0,bad=True)
        await q.answer("❌ לא נכון!",show_alert=True)

async def end_tourn(ctx, cid):
    t=tourn[cid]; t["active"]=False
    board=sorted(t["round_scores"].items(),key=lambda x:x[1]["pts"],reverse=True)
    medals=["🥇","🥈","🥉"]; lines=["🎯 *הטורניר הסתיים!*\n"]
    for i,(uid,d) in enumerate(board): lines.append(f"{medals[i] if i<3 else f'{i+1}.'} {d['name']} — {d['pts']} נק׳")
    if board: lines.append(f"\n👑 המנצח: *{board[0][1]['name']}*!")
    await ctx.bot.send_message(cid,"\n".join(lines),parse_mode="Markdown",reply_markup=after_menu())

# ── Scores ────────────────────────────────────────────────────────────────────
async def scores_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    track(update.effective_chat.id,update.effective_user.id)
    board=s_board(update.effective_chat.id)
    if not board: await update.message.reply_text("אין ניקוד!"); return
    medals=["🥇","🥈","🥉"]; lines=["🏆 *טבלת המובילים*\n"]
    for i,(n,p) in enumerate(board): lines.append(f"{medals[i] if i<3 else f'{i+1}.'} {n} — *{p}* נק׳")
    await update.message.reply_text("\n".join(lines),parse_mode="Markdown",reply_markup=after_menu())

async def reset_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cid=update.effective_chat.id
    m=await ctx.bot.get_chat_member(cid,update.effective_user.id)
    if m.status not in ("administrator","creator"): await update.message.reply_text("❌ רק אדמין!"); return
    SCORES[str(cid)]={};  await update.message.reply_text("✅ הניקוד אופס!")

# ── Daily ─────────────────────────────────────────────────────────────────────
async def send_daily(ctx: ContextTypes.DEFAULT_TYPE):
    for cid in list(chat_members.keys()):
        try:
            diff=random.choice(["easy","medium","hard"])
            await ctx.bot.send_message(cid,f"📅 *שאלת היום!* {DIFF_LABEL[diff]}",parse_mode="Markdown")
            await ask_trivia(ctx,cid,diff)
        except Exception as e: print(f"daily error {cid}: {e}")

# ── Truth or Lie ──────────────────────────────────────────────────────────────
async def tol_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cid=update.effective_chat.id; track(cid,update.effective_user.id)
    tol[cid]={"submissions":[],"votes":{},"active":True}
    await update.message.reply_text("🤥 *אמת או שקר!*\nלחצו ׳שלח עובדה׳:",parse_mode="Markdown",reply_markup=tol_menu())

async def do_tol_reveal(ctx, cid):
    if cid not in tol or not tol[cid]["active"]: return
    subs=tol[cid]["submissions"]
    if len(subs)<2: await ctx.bot.send_message(cid,"צריך לפחות 2 שחקנים!"); return
    for i,(uid,name,text,is_truth) in enumerate(subs):
        kb=[[InlineKeyboardButton("✅ אמת",callback_data=f"tol_{i}_true_{uid}"),InlineKeyboardButton("❌ שקר",callback_data=f"tol_{i}_false_{uid}")]]
        await ctx.bot.send_message(cid,f"🤔 *עובדה #{i+1}* ({name})\n\n_{text}_",reply_markup=InlineKeyboardMarkup(kb),parse_mode="Markdown")

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
            if i==idx and ans==correct and vid!=sid: s_add(cid,vid,vn,20,ok=True); winners.append(vn)
        await q.edit_message_text(f"{q.message.text}\n\n🎯 *{ans_text}*\nניחשו נכון: {', '.join(winners) or 'אף אחד'} (+20 נק׳)",parse_mode="Markdown")

# ── Story ─────────────────────────────────────────────────────────────────────
async def story_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cid=update.effective_chat.id; track(cid,update.effective_user.id)
    opener=random.choice(STORY_OPENERS)
    story[cid]={"opener":opener,"entries":[],"last_user":None,"active":True}
    await update.message.reply_text(f"📖 *סיפור קבוצתי!*\n\n_{opener}_\n\nלחצו ׳הוסף׳:",parse_mode="Markdown",reply_markup=story_kb())

# ── Text handler ──────────────────────────────────────────────────────────────
async def handle_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cid=update.effective_chat.id; user=update.effective_user
    uid=user.id; name=get_name(user); text=update.message.text.strip()
    track(cid,uid)
    if ctx.user_data.get("awaiting_story")==cid:
        del ctx.user_data["awaiting_story"]
        if cid not in story or not story[cid].get("active"): await update.message.reply_text("אין סיפור פעיל."); return
        if story[cid]["last_user"]==uid: await update.message.reply_text("⏳ תן לאחרים קודם! 😄"); return
        story[cid]["entries"].append((uid,name,text)); story[cid]["last_user"]=uid
        s_add(cid,uid,name,10,ok=True); count=len(story[cid]["entries"])
        extra=f"\n\n🎲 _וואו {count} משפטים!_" if count%5==0 else ""
        await update.message.reply_text(f"✍️ *{name}*: _{text}_ +10 נק׳{extra}",parse_mode="Markdown",reply_markup=story_kb())
        return
    if ctx.user_data.get("awaiting_tol")==cid:
        del ctx.user_data["awaiting_tol"]
        if cid not in tol or not tol[cid]["active"]: return
        tol[cid]["submissions"].append((uid,name,text,random.choice([True,False])))
        await update.message.reply_text(f"✅ *{name}* שלח עובדה! 🤫\nמי הבא?",parse_mode="Markdown",reply_markup=tol_menu())
        return

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    app=Application.builder().token(TOKEN).build()
    app.job_queue.run_daily(send_daily,time=dtime(hour=10,minute=0))
    app.job_queue.run_repeating(check_alerts,interval=5,first=10)
    app.add_handler(CommandHandler("start",start))
    app.add_handler(CommandHandler("scores",scores_cmd))
    app.add_handler(CommandHandler("reset",reset_cmd))
    app.add_handler(CommandHandler("trivia",trivia_cmd))
    app.add_handler(CommandHandler("tournament",tournament_cmd))
    app.add_handler(CommandHandler("truthorlie",tol_cmd))
    app.add_handler(CommandHandler("story",story_cmd))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS,new_member))
    app.add_handler(CallbackQueryHandler(ans_callback, pattern="^ans_"))
    app.add_handler(CallbackQueryHandler(tans_callback,pattern="^tans_"))
    app.add_handler(CallbackQueryHandler(cb_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,handle_text))
    print("🤖 GameBot Pro רץ!")
    app.run_polling()

if __name__=="__main__":
    main()
