
from collections import defaultdict

class ResonanceMonitor:
    def __init__(self):
        self.hit_counts = defaultdict(int)
        self.max_hits = 0

    def process(self, func_ids):
        for fid in func_ids:
            self.hit_counts[fid] += 1
            if self.hit_counts[fid] > self.max_hits:
                self.max_hits = self.hit_counts[fid]

    def top_n(self, n=5):
        return sorted(self.hit_counts.items(), key=lambda x: -x[1])[:n]
