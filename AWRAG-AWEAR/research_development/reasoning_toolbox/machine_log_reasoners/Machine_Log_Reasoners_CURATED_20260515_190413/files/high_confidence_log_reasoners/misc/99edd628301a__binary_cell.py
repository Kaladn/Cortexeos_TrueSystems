class BinaryCell:
    """
    Represents a binary cell for a word with its context relationships.
    
    This is a simplified version of the binary cell structure for demonstration purposes.
    """
    
    def __init__(self, word, token_id=None, frequency=0, tone_signature=0):
        """
        Initialize a binary cell.
        
        Args:
            word: The word string
            token_id: Unique identifier for the word/token
            frequency: Global occurrence frequency
            tone_signature: Encoded tonal fingerprint
        """
        self.word = word
        self.token_id = token_id or hash(word) % 100000
        self.frequency = frequency
        self.tone_signature = tone_signature
        self.before_context = []  # List of (token_id, frequency, tone_id) tuples
        self.after_context = []   # List of (token_id, frequency, tone_id) tuples
        self.overflow_before = None
        self.overflow_after = None
    
    def add_before_context(self, token_id, frequency=1, tone_id=0):
        """Add a word that appears before this word in context."""
        self.before_context.append((token_id, frequency, tone_id))
    
    def add_after_context(self, token_id, frequency=1, tone_id=0):
        """Add a word that appears after this word in context."""
        self.after_context.append((token_id, frequency, tone_id))
    
    def to_dict(self):
        """Convert to dictionary representation."""
        return {
            "word": self.word,
            "token_id": self.token_id,
            "frequency": self.frequency,
            "tone_signature": self.tone_signature,
            "before_context": self.before_context,
            "after_context": self.after_context,
            "has_overflow": bool(self.overflow_before or self.overflow_after)
        }


class NeuralIndex:
    """
    Simplified neural index for demonstration purposes.
    
    In a real implementation, this would be a B+Tree with bloom filter.
    """
    
    def __init__(self):
        """Initialize an empty index."""
        self.word_to_token_id = {}
        self.token_id_to_word = {}
        self.cells = {}  # word -> BinaryCell
    
    def add_word(self, word, token_id=None):
        """
        Add a word to the index.
        
        Args:
            word: The word string
            token_id: Optional token ID (generated if not provided)
            
        Returns:
            The token ID
        """
        if word in self.word_to_token_id:
            return self.word_to_token_id[word]
        
        token_id = token_id or hash(word) % 100000
        self.word_to_token_id[word] = token_id
        self.token_id_to_word[token_id] = word
        
        return token_id
    
    def get_token_id(self, word):
        """Get token ID for a word."""
        return self.word_to_token_id.get(word)
    
    def get_word(self, token_id):
        """Get word for a token ID."""
        return self.token_id_to_word.get(token_id)
    
    def add_cell(self, cell):
        """Add a binary cell to the index."""
        self.cells[cell.word] = cell
        self.word_to_token_id[cell.word] = cell.token_id
        self.token_id_to_word[cell.token_id] = cell.word
    
    def get_cell(self, word):
        """Get binary cell for a word."""
        return self.cells.get(word)


class NeuralMemory:
    """
    Simplified neural memory system for demonstration purposes.
    
    This class provides a simplified interface to the binary cell structure.
    """
    
    def __init__(self):
        """Initialize an empty neural memory."""
        self.index = NeuralIndex()
    
    def add_word(self, word, frequency=1, tone_signature=0):
        """
        Add a word to the neural memory.
        
        Args:
            word: The word string
            frequency: Global occurrence frequency
            tone_signature: Encoded tonal fingerprint
            
        Returns:
            The binary cell
        """
        token_id = self.index.add_word(word)
        
        # Create or update cell
        cell = self.index.get_cell(word)
        if not cell:
            cell = BinaryCell(word, token_id, frequency, tone_signature)
            self.index.add_cell(cell)
        else:
            cell.frequency += frequency
        
        return cell
    
    def add_context(self, word1, word2, frequency=1, tone_id=0):
        """
        Add context relationship between two words.
        
        Args:
            word1: The first word
            word2: The second word (appears after word1)
            frequency: Occurrence frequency of this relationship
            tone_id: Tonal identifier for this relationship
        """
        # Add words if they don't exist
        cell1 = self.add_word(word1)
        cell2 = self.add_word(word2)
        
        # Add context relationships
        cell1.add_after_context(cell2.token_id, frequency, tone_id)
        cell2.add_before_context(cell1.token_id, frequency, tone_id)
    
    def get_context(self, word, include_before=True, include_after=True, limit=10):
        """
        Get context for a word.
        
        Args:
            word: The word to get context for
            include_before: Whether to include words that appear before
            include_after: Whether to include words that appear after
            limit: Maximum number of context words to return per direction
            
        Returns:
            Dictionary with before_context and after_context lists
        """
        cell = self.index.get_cell(word)
        if not cell:
            return {"word": word, "before_context": [], "after_context": []}
        
        result = {"word": word}
        
        # Process before context
        before_context = []
        if include_before:
            for token_id, freq, _ in sorted(cell.before_context, key=lambda x: x[1], reverse=True)[:limit]:
                context_word = self.index.get_word(token_id)
                if context_word:
                    before_context.append({"word": context_word, "frequency": freq})
        
        # Process after context
        after_context = []
        if include_after:
            for token_id, freq, _ in sorted(cell.after_context, key=lambda x: x[1], reverse=True)[:limit]:
                context_word = self.index.get_word(token_id)
                if context_word:
                    after_context.append({"word": context_word, "frequency": freq})
        
        result["before_context"] = before_context
        result["after_context"] = after_context
        
        return result
    
    def initialize_sample_data(self):
        """Initialize with sample data for demonstration."""
        # Add some common words
        words = ["neural", "network", "memory", "artificial", "intelligence", 
                "learning", "deep", "brain", "model", "data", "processing",
                "algorithm", "system", "computer", "machine"]
        
        for word in words:
            self.add_word(word, frequency=len(word) * 10)
        
        # Add context relationships
        relationships = [
            ("artificial", "intelligence", 45),
            ("artificial", "neural", 42),
            ("neural", "network", 56),
            ("neural", "memory", 35),
            ("neural", "processing", 22),
            ("deep", "neural", 28),
            ("deep", "learning", 40),
            ("machine", "learning", 38),
            ("computer", "memory", 25),
            ("brain", "model", 18),
            ("data", "processing", 30),
            ("learning", "algorithm", 22),
            ("learning", "model", 28),
            ("network", "architecture", 20),
            ("memory", "system", 24),
            ("intelligence", "system", 18),
            ("neural", "pathways", 18),
            ("neural", "connections", 14),
            ("biological", "neural", 15),
            ("advanced", "neural", 12),
            ("human", "neural", 10)
        ]
        
        for word1, word2, freq in relationships:
            self.add_context(word1, word2, freq)
        
        return self
