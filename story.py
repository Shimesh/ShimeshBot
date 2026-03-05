import random

QUESTIONS = [
    {"question": "מהי הבירה של אוסטרליה?", "options": {"א": "סידני", "ב": "קנברה", "ג": "מלבורן", "ד": "פרת׳"}, "answer": "ב"},
    {"question": "כמה גרמים יש בקילוגרם?", "options": {"א": "100", "ב": "500", "ג": "1000", "ד": "10000"}, "answer": "ג"},
    {"question": "מי צייר את המונה ליזה?", "options": {"א": "מיכלאנג׳לו", "ב": "רפאל", "ג": "לאונרדו דה וינצ׳י", "ד": "פיקאסו"}, "answer": "ג"},
    {"question": "מהי כוכב הלכת הגדול ביותר במערכת השמש?", "options": {"א": "שבתאי", "ב": "צדק", "ג": "אורנוס", "ד": "נפטון"}, "answer": "ב"},
    {"question": "כמה צלעות יש למשושה?", "options": {"א": "5", "ב": "6", "ג": "7", "ד": "8"}, "answer": "ב"},
    {"question": "באיזו שנה הוקם מדינת ישראל?", "options": {"א": "1945", "ב": "1947", "ג": "1948", "ד": "1950"}, "answer": "ג"},
    {"question": "מהו היסוד הכימי עם הסימול Au?", "options": {"א": "כסף", "ב": "אלומיניום", "ג": "זהב", "ד": "נחושת"}, "answer": "ג"},
    {"question": "כמה שחקנים יש בקבוצת כדורגל?", "options": {"א": "9", "ב": "10", "ג": "11", "ד": "12"}, "answer": "ג"},
    {"question": "מה הוא הנהר הארוך ביותר בעולם?", "options": {"א": "האמזונס", "ב": "הנילוס", "ג": "המיסיסיפי", "ד": "היאנגצה"}, "answer": "ב"},
    {"question": "כמה צבעים יש בקשת בענן?", "options": {"א": "5", "ב": "6", "ג": "7", "ד": "8"}, "answer": "ג"},
    {"question": "מה היא עיר הבירה של יפן?", "options": {"א": "אוסקה", "ב": "קיוטו", "ג": "טוקיו", "ד": "הירושימה"}, "answer": "ג"},
    {"question": "כמה אוקיינוסים יש על כדור הארץ?", "options": {"א": "3", "ב": "4", "ג": "5", "ד": "6"}, "answer": "ג"},
    {"question": "מי כתב את רומיאו ויוליה?", "options": {"א": "דיקנס", "ב": "שקספיר", "ג": "מולייר", "ד": "גתה"}, "answer": "ב"},
    {"question": "מהי המדינה הגדולה ביותר בעולם?", "options": {"א": "קנדה", "ב": "סין", "ג": "ארצות הברית", "ד": "רוסיה"}, "answer": "ד"},
    {"question": "כמה שניות יש בשעה?", "options": {"א": "360", "ב": "3600", "ג": "36000", "ד": "600"}, "answer": "ב"},
    {"question": "מה הוא פירות הציטרוס הגדול ביותר?", "options": {"א": "לימון", "ב": "תפוז", "ג": "פומלה", "ד": "אשכולית"}, "answer": "ג"},
    {"question": "איזה חיה ידועה כ׳מלך הג׳ונגל׳?", "options": {"א": "נמר", "ב": "אריה", "ג": "פיל", "ד": "גורילה"}, "answer": "ב"},
    {"question": "כמה חדשים יש בשנה שבה פברואר הוא 29 יום?", "options": {"א": "11", "ב": "12", "ג": "13", "ד": "תמיד 12"}, "answer": "ד"},
    {"question": "מה היא עיר הבירה של ברזיל?", "options": {"א": "ריו דה ז׳ניירו", "ב": "סאו פאולו", "ג": "ברזיליה", "ד": "סלבדור"}, "answer": "ג"},
    {"question": "כמה עצמות יש בגוף האדם הבוגר?", "options": {"א": "186", "ב": "206", "ג": "226", "ד": "246"}, "answer": "ב"},
]

class TriviaGame:
    def __init__(self):
        self.active = False
        self.current_q = None
        self.answered = {}  # user_id -> answer
        self.correct_count = 0

    def start(self):
        self.current_q = random.choice(QUESTIONS)
        self.active = True
        self.answered = {}
        self.correct_count = 0
        return self.current_q

    def correct_answer(self):
        if not self.current_q:
            return ""
        key = self.current_q["answer"]
        return f"{key}) {self.current_q['options'][key]}"

    def points_for_next(self):
        """First correct = 50pts, then 30, then 20"""
        if self.correct_count == 0:
            return 50
        elif self.correct_count == 1:
            return 30
        return 20

    def answer(self, user_id, text):
        if user_id in self.answered:
            return "already"
        self.answered[user_id] = text
        # Accept letter or full answer text
        correct_letter = self.current_q["answer"]
        correct_text = self.current_q["options"][correct_letter].upper()
        if text == correct_letter or text == correct_text:
            self.correct_count += 1
            return "correct"
        return "wrong"
