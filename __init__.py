class TruthOrLieGame:
    def __init__(self):
        self.active = True
        self.submissions = []  # list of (user_id, name, text)
        self.votes = {}        # (voter_id, idx) -> vote
        self.revealed = set()  # indexes already revealed
        # Truths defined by submitter (randomly assigned for demo)
        self.truths = {}       # idx -> bool (True = truth, False = lie)

    def submit(self, user_id, name, text):
        """Add a submission. Randomly marks as truth/lie for the game."""
        import random
        idx = len(self.submissions)
        self.submissions.append((user_id, name, text))
        # In a real game, the submitter decides; here we randomly assign
        # but the submitter knows the truth themselves
        self.truths[idx] = random.choice([True, False])

    def vote(self, voter_id, voter_name, idx, vote_str):
        """
        Returns:
          'already'  — already voted on this
          None       — vote registered, not last
          (is_truth, [(correct_voter_id, name)]) — last vote, reveal result
        """
        key = (voter_id, idx)
        if key in self.votes:
            return "already"
        self.votes[key] = vote_str  # 'true' or 'false'
        # Count votes for this idx
        votes_for_idx = {k: v for k, v in self.votes.items() if k[1] == idx}
        # Reveal after 3 votes or if all non-submitters voted
        submitter_id = self.submissions[idx][0]
        if len(votes_for_idx) >= 3 and idx not in self.revealed:
            self.revealed.add(idx)
            is_truth = self.truths[idx]
            correct_answer = "true" if is_truth else "false"
            correct_voters = [
                (vid, self._find_name(vid))
                for (vid, i), ans in self.votes.items()
                if i == idx and ans == correct_answer and vid != submitter_id
            ]
            return (is_truth, correct_voters)
        return None

    def _find_name(self, user_id):
        # Try to get name from submissions
        for uid, name, _ in self.submissions:
            if uid == user_id:
                return name
        return "שחקן"
