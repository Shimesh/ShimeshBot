class StoryGame:
    def __init__(self, opener: str):
        self.active = True
        self.opener = opener
        self.entries = []   # list of (user_id, name, text)
        self.last_user = None

    def add(self, user_id, name, text):
        self.entries.append((user_id, name, text))
        self.last_user = user_id

    def get_full_story(self):
        parts = [self.opener]
        for _, _, text in self.entries:
            parts.append(text)
        return " ".join(parts)
