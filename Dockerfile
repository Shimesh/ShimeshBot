import json
import os

SCORES_FILE = "data/scores.json"

class ScoreManager:
    def __init__(self):
        os.makedirs("data", exist_ok=True)
        self._load()

    def _load(self):
        if os.path.exists(SCORES_FILE):
            with open(SCORES_FILE, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        else:
            self.data = {}

    def _save(self):
        with open(SCORES_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def add(self, chat_id, user_id, name, points):
        cid = str(chat_id)
        uid = str(user_id)
        if cid not in self.data:
            self.data[cid] = {}
        if uid not in self.data[cid]:
            self.data[cid][uid] = {"name": name, "points": 0}
        self.data[cid][uid]["points"] += points
        self.data[cid][uid]["name"] = name  # update name
        self._save()

    def get_leaderboard(self, chat_id):
        cid = str(chat_id)
        if cid not in self.data:
            return []
        players = [
            (v["name"], v["points"])
            for v in self.data[cid].values()
        ]
        return sorted(players, key=lambda x: x[1], reverse=True)[:10]

    def reset(self, chat_id):
        cid = str(chat_id)
        self.data[cid] = {}
        self._save()
