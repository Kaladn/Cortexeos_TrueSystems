from collections import defaultdict

class WindowBuilder:
    def __init__(self, config):
        self.config = config
        self.window_size = self.config["window_size"]
        self.lexicon_counts = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))

    def process(self, tokens):
        """Slides a 6-1-6 window over the token stream and updates counts."""
        token_list = list(tokens)
        for i, center_token in enumerate(token_list):
            center_norm = center_token["norm"]

            # Process previous tokens
            for j in range(1, self.window_size + 1):
                if i - j >= 0:
                    neighbor_token = token_list[i - j]
                    neighbor_norm = neighbor_token["norm"]
                    self.lexicon_counts[center_norm][-j][neighbor_norm] += 1

            # Process next tokens
            for j in range(1, self.window_size + 1):
                if i + j < len(token_list):
                    neighbor_token = token_list[i + j]
                    neighbor_norm = neighbor_token["norm"]
                    self.lexicon_counts[center_norm][j][neighbor_norm] += 1

    def get_lexicon_counts(self):
        return self.lexicon_counts
