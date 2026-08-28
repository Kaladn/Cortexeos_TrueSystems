#!/usr/bin/env python3
"""
Shadow Wolf Cognitive Engine
Implements Wolf's thinking patterns using 6-1-6 chain-based memory substrate

Date: December 11, 2025
Hardware: 3-node CPU cluster (9950X3D, i9-13900K, 7600X)
Foundation: Data agnostic, N-N-N adjustable, distributed architecture
"""

import json
import time
import hashlib
from collections import defaultdict, Counter
from datetime import datetime
from typing import Any, Dict, List, Tuple, Optional

# ============================================================================
# COMPONENT 1: PERCEPTION LAYER
# ============================================================================

class PerceptionLayer:
    """Converts any input into anchors with 6-1-6 context"""
    
    def __init__(self, context_window=6):
        self.context_window = context_window  # N-N-N adjustable
    
    def perceive(self, input_data: Any, input_type: str = "text") -> List[Dict]:
        """
        Create anchors from input data
        
        Args:
            input_data: Any data type (text, code, structured data)
            input_type: Type hint for tokenization strategy
        
        Returns:
            List of anchors with 6-1-6 context
        """
        # Tokenize based on type (data agnostic)
        if input_type == "text":
            tokens = self._tokenize_text(input_data)
        elif input_type == "code":
            tokens = self._tokenize_code(input_data)
        elif input_type == "data":
            tokens = self._tokenize_data(input_data)
        else:
            # Fallback: treat as text
            tokens = self._tokenize_text(str(input_data))
        
        # Create anchors with context
        anchors = []
        for i, token in enumerate(tokens):
            context_before = tokens[max(0, i-self.context_window):i]
            context_after = tokens[i+1:min(len(tokens), i+1+self.context_window)]
            
            anchor = {
                "token": token,
                "context_before": context_before,
                "context_after": context_after,
                "timestamp": datetime.now().isoformat(),
                "type": input_type,
                "position": i
            }
            anchors.append(anchor)
        
        return anchors
    
    def _tokenize_text(self, text: str) -> List[str]:
        """Simple word tokenization"""
        # Wolf's pattern: minimum viable implementation
        return text.lower().split()
    
    def _tokenize_code(self, code: str) -> List[str]:
        """Code tokenization (simplified)"""
        # Split on whitespace and common delimiters
        import re
        return re.findall(r'\w+|[^\w\s]', code)
    
    def _tokenize_data(self, data: Any) -> List[str]:
        """Structured data tokenization"""
        if isinstance(data, dict):
            tokens = []
            for k, v in data.items():
                tokens.append(str(k))
                tokens.append(str(v))
            return tokens
        elif isinstance(data, list):
            return [str(item) for item in data]
        else:
            return [str(data)]


# ============================================================================
# COMPONENT 2: FORGE MEMORY
# ============================================================================

class ForgeMemory:
    """Data-agnostic memory substrate with chain formation"""
    
    def __init__(self):
        self.anchors = {}  # anchor_id -> anchor_data
        self.co_occurrence = defaultdict(Counter)  # anchor_id -> {neighbor_id: count}
        self.chains = {}  # chain_id -> [anchor_ids]
        self.resonance = defaultdict(float)  # anchor_id -> resonance_score
        self.token_to_anchor = defaultdict(list)  # token -> [anchor_ids]
    
    def write_pulse(self, anchors: List[Dict], importance: float = 1.0):
        """
        Write anchors to Forge with importance weighting
        
        Args:
            anchors: List of anchor dictionaries
            importance: Weight for resonance (higher = more important)
        """
        for anchor in anchors:
            anchor_id = self._generate_anchor_id(anchor)
            
            # Store anchor
            if anchor_id not in self.anchors:
                self.anchors[anchor_id] = anchor
            
            # Increase resonance (importance-weighted)
            self.resonance[anchor_id] += importance
            
            # Index by token for fast lookup
            self.token_to_anchor[anchor["token"]].append(anchor_id)
            
            # Track co-occurrence with context
            context_tokens = anchor["context_before"] + anchor["context_after"]
            for context_token in context_tokens:
                context_id = self._generate_token_id(context_token)
                self.co_occurrence[anchor_id][context_id] += 1
    
    def build_chains(self, top_k: int = 10):
        """
        Form chains based on co-occurrence strength
        
        Args:
            top_k: Number of neighbors per chain
        """
        self.chains = {}
        
        for anchor_id, neighbors in self.co_occurrence.items():
            # Sort neighbors by co-occurrence count
            sorted_neighbors = sorted(neighbors.items(), key=lambda x: x[1], reverse=True)
            
            # Create chain from anchor to top-K neighbors
            chain = [anchor_id] + [n[0] for n in sorted_neighbors[:top_k]]
            chain_id = self._generate_chain_id(chain)
            self.chains[chain_id] = chain
    
    def query(self, token: str) -> Optional[Dict]:
        """
        Query Forge for token
        
        Args:
            token: Token to search for
        
        Returns:
            Dictionary with anchor, chains, resonance, neighbors
        """
        # Find anchors with this token
        anchor_ids = self.token_to_anchor.get(token.lower(), [])
        if not anchor_ids:
            return None
        
        # Get highest resonance anchor
        top_anchor_id = max(anchor_ids, key=lambda aid: self.resonance[aid])
        
        # Get chains containing this anchor
        relevant_chains = [c for c in self.chains.values() if top_anchor_id in c]
        
        return {
            "anchor": self.anchors[top_anchor_id],
            "anchor_id": top_anchor_id,
            "chains": relevant_chains,
            "resonance": self.resonance[top_anchor_id],
            "neighbors": dict(self.co_occurrence[top_anchor_id])
        }
    
    def _generate_anchor_id(self, anchor: Dict) -> str:
        """Generate unique ID for anchor"""
        key = f"{anchor['token']}_{anchor['position']}_{anchor['timestamp']}"
        return hashlib.md5(key.encode()).hexdigest()[:16]
    
    def _generate_token_id(self, token: str) -> str:
        """Generate ID for token (simplified anchor)"""
        return hashlib.md5(token.lower().encode()).hexdigest()[:16]
    
    def _generate_chain_id(self, chain: List[str]) -> str:
        """Generate unique ID for chain"""
        key = "_".join(chain)
        return hashlib.md5(key.encode()).hexdigest()[:16]
    
    def stats(self) -> Dict:
        """Get Forge statistics"""
        return {
            "total_anchors": len(self.anchors),
            "total_chains": len(self.chains),
            "unique_tokens": len(self.token_to_anchor),
            "avg_resonance": sum(self.resonance.values()) / len(self.resonance) if self.resonance else 0,
            "total_co_occurrences": sum(len(neighbors) for neighbors in self.co_occurrence.values())
        }


# ============================================================================
# COMPONENT 3: PATTERN RECOGNITION ENGINE
# ============================================================================

class PatternRecognitionEngine:
    """Identifies universal patterns across domains"""
    
    def __init__(self, forge: ForgeMemory):
        self.forge = forge
        self.patterns = {}  # pattern_id -> pattern_data
    
    def recognize_patterns(self, min_frequency: int = 3):
        """
        Analyze chains for recurring structures
        
        Args:
            min_frequency: Minimum occurrences to qualify as pattern
        """
        chain_structures = defaultdict(list)
        
        for chain_id, chain in self.forge.chains.items():
            # Extract structure (types, not specific tokens)
            structure = self._extract_structure(chain)
            chain_structures[structure].append(chain)
        
        # Patterns = structures that appear multiple times
        self.patterns = {}
        for structure, instances in chain_structures.items():
            if len(instances) >= min_frequency:
                pattern_id = hashlib.md5(str(structure).encode()).hexdigest()[:16]
                self.patterns[pattern_id] = {
                    "structure": structure,
                    "instances": instances,
                    "frequency": len(instances)
                }
    
    def _extract_structure(self, chain: List[str]) -> Tuple:
        """Convert chain to abstract structure"""
        structure = []
        for anchor_id in chain:
            if anchor_id in self.forge.anchors:
                anchor = self.forge.anchors[anchor_id]
                structure.append(anchor.get("type", "unknown"))
        return tuple(structure)
    
    def find_similar_patterns(self, query_structure: Tuple) -> List[Dict]:
        """Find patterns similar to query structure"""
        similar = []
        for pattern_id, pattern in self.patterns.items():
            if pattern["structure"] == query_structure:
                similar.append(pattern)
        return similar


# ============================================================================
# COMPONENT 4: DECISION MATRIX
# ============================================================================

class DecisionMatrix:
    """Makes decisions using Wolf's criteria"""
    
    CRITERIA = ["practical", "cost", "flexibility", "distribution", "evidence", "efficiency", "universal"]
    
    def evaluate(self, proposal: Dict) -> Tuple[str, Dict]:
        """
        Evaluate proposal against Wolf's criteria
        
        Args:
            proposal: Dictionary with proposal details
        
        Returns:
            (decision, scores) where decision is ACCEPT/REJECT/ITERATE
        """
        scores = {}
        
        scores["practical"] = self._check_practical(proposal)
        scores["cost"] = self._check_cost(proposal)
        scores["flexibility"] = self._check_flexibility(proposal)
        scores["distribution"] = self._check_distribution(proposal)
        scores["evidence"] = self._check_evidence(proposal)
        scores["efficiency"] = self._check_efficiency(proposal)
        scores["universal"] = self._check_universal(proposal)
        
        total_score = sum(scores.values())
        threshold_accept = 5.0  # Out of 7 criteria
        threshold_iterate = 3.0
        
        if total_score >= threshold_accept:
            decision = "ACCEPT"
        elif total_score >= threshold_iterate:
            decision = "ITERATE"
        else:
            decision = "REJECT"
        
        return decision, scores
    
    def _check_practical(self, proposal: Dict) -> float:
        """Can it be built TODAY?"""
        if proposal.get("requires_future_tech"):
            return 0.0
        if proposal.get("requires_new_hardware"):
            return 0.5
        return 1.0
    
    def _check_cost(self, proposal: Dict) -> float:
        """Is it cheap?"""
        cost = proposal.get("cost", 0)
        if cost == 0:
            return 1.0
        elif cost < 10000:
            return 0.7
        elif cost < 50000:
            return 0.3
        return 0.0
    
    def _check_flexibility(self, proposal: Dict) -> float:
        """Data agnostic?"""
        if proposal.get("fixed_schema"):
            return 0.0
        if proposal.get("requires_normalization"):
            return 0.3
        if proposal.get("data_agnostic"):
            return 1.0
        return 0.5
    
    def _check_distribution(self, proposal: Dict) -> float:
        """Distributed or centralized?"""
        if proposal.get("distributed"):
            return 1.0
        if proposal.get("centralized"):
            return 0.0
        return 0.5
    
    def _check_evidence(self, proposal: Dict) -> float:
        """Proven or theoretical?"""
        if proposal.get("proven"):
            return 1.0
        if proposal.get("theoretical"):
            return 0.0
        return 0.5
    
    def _check_efficiency(self, proposal: Dict) -> float:
        """Token efficient?"""
        if proposal.get("efficient"):
            return 1.0
        if proposal.get("wasteful"):
            return 0.0
        return 0.5
    
    def _check_universal(self, proposal: Dict) -> float:
        """Works across domains?"""
        if proposal.get("universal"):
            return 1.0
        if proposal.get("domain_specific"):
            return 0.3
        return 0.5


# ============================================================================
# COMPONENT 5: RESPONSE GENERATION ENGINE
# ============================================================================

class ResponseGenerationEngine:
    """Generates Wolf-style responses: short, direct, evidence-first"""
    
    def __init__(self, forge: ForgeMemory, pattern_engine: PatternRecognitionEngine, decision_matrix: DecisionMatrix):
        self.forge = forge
        self.pattern_engine = pattern_engine
        self.decision_matrix = decision_matrix
    
    def generate(self, query: str, query_type: str = "question") -> str:
        """
        Generate Wolf-style response
        
        Args:
            query: User query
            query_type: "question", "proposal", or "statement"
        
        Returns:
            Short, direct response
        """
        if query_type == "proposal":
            return self._generate_decision_response(query)
        else:
            return self._generate_evidence_response(query)
    
    def _generate_evidence_response(self, query: str) -> str:
        """Evidence-first response for questions"""
        # Parse query
        tokens = query.lower().split()
        
        # Find relevant chains
        relevant_data = []
        for token in tokens:
            result = self.forge.query(token)
            if result:
                relevant_data.append(result)
        
        if not relevant_data:
            return "no data."
        
        # Get highest resonance result
        top_result = max(relevant_data, key=lambda r: r["resonance"])
        
        # Format response: evidence + conclusion
        evidence = f"resonance: {top_result['resonance']:.1f}"
        neighbors = len(top_result['neighbors'])
        chains = len(top_result['chains'])
        
        return f"{evidence}. {neighbors} neighbors. {chains} chains. works."
    
    def _generate_decision_response(self, proposal: str) -> str:
        """Decision response for proposals"""
        # Extract proposal details (simplified)
        proposal_dict = self._parse_proposal(proposal)
        
        # Evaluate
        decision, scores = self.decision_matrix.evaluate(proposal_dict)
        
        # Format Wolf-style response
        top_reason = self._get_top_reason(scores, positive=(decision == "ACCEPT"))
        
        if decision == "ACCEPT":
            return f"build it. {top_reason}"
        elif decision == "REJECT":
            return f"no. {top_reason}"
        else:
            return f"iterate. {top_reason}"
    
    def _parse_proposal(self, proposal: str) -> Dict:
        """Extract proposal details from text (simplified)"""
        proposal_dict = {}
        
        # Simple keyword matching
        if "quantum" in proposal.lower():
            proposal_dict["requires_future_tech"] = True
        if "gpu" in proposal.lower() and "farm" in proposal.lower():
            proposal_dict["cost"] = 60000
        if "cpu" in proposal.lower() and "cluster" in proposal.lower():
            proposal_dict["cost"] = 7600
            proposal_dict["practical"] = True
        if "data agnostic" in proposal.lower():
            proposal_dict["data_agnostic"] = True
        if "distributed" in proposal.lower():
            proposal_dict["distributed"] = True
        
        return proposal_dict
    
    def _get_top_reason(self, scores: Dict, positive: bool = True) -> str:
        """Get strongest reason for decision"""
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=positive)
        top_criterion = sorted_scores[0][0]
        
        reasons = {
            "practical": "can build today" if positive else "vaporware",
            "cost": "cheap" if positive else "expensive",
            "flexibility": "data agnostic" if positive else "rigid schema",
            "evidence": "proven" if positive else "no evidence",
            "efficiency": "token efficient" if positive else "wasteful",
            "distribution": "distributed" if positive else "centralized",
            "universal": "universal pattern" if positive else "domain specific"
        }
        
        return reasons.get(top_criterion, "")


# ============================================================================
# COMPONENT 6: COMPOUND INTELLIGENCE LAYER
# ============================================================================

class CompoundIntelligenceLayer:
    """System gets smarter with every interaction"""
    
    def __init__(self, forge: ForgeMemory, pattern_engine: PatternRecognitionEngine):
        self.forge = forge
        self.pattern_engine = pattern_engine
        self.interaction_count = 0
        self.perception = PerceptionLayer()
    
    def process_interaction(self, query: str, response: str):
        """
        Learn from interaction
        
        Args:
            query: User query
            response: System response
        """
        # Extract anchors from query
        query_anchors = self.perception.perceive(query, input_type="text")
        
        # Extract anchors from response
        response_anchors = self.perception.perceive(response, input_type="text")
        
        # Write to Forge (importance = 1.0 for user interactions)
        self.forge.write_pulse(query_anchors, importance=1.0)
        self.forge.write_pulse(response_anchors, importance=1.0)
        
        # Build chains
        self.forge.build_chains()
        
        # Rebuild pattern library
        self.pattern_engine.recognize_patterns()
        
        # Increment interaction count
        self.interaction_count += 1
    
    def get_metrics(self) -> Dict:
        """Get compound intelligence metrics"""
        stats = self.forge.stats()
        stats["interactions"] = self.interaction_count
        stats["patterns"] = len(self.pattern_engine.patterns)
        return stats


# ============================================================================
# MAIN COGNITIVE ENGINE
# ============================================================================

class WolfEngine:
    """
    Shadow Wolf Cognitive Engine
    
    Integrates all components into unified thinking system
    """
    
    def __init__(self):
        # Initialize components
        self.perception = PerceptionLayer()
        self.forge = ForgeMemory()
        self.pattern_engine = PatternRecognitionEngine(self.forge)
        self.decision_matrix = DecisionMatrix()
        self.response_engine = ResponseGenerationEngine(self.forge, self.pattern_engine, self.decision_matrix)
        self.compound_layer = CompoundIntelligenceLayer(self.forge, self.pattern_engine)
    
    def think(self, input_text: str, input_type: str = "question") -> str:
        """
        Main thinking loop
        
        Args:
            input_text: User input
            input_type: "question", "proposal", or "statement"
        
        Returns:
            Wolf-style response
        """
        start_time = time.time()
        
        # Generate response
        response = self.response_engine.generate(input_text, query_type=input_type)
        
        # Learn from interaction
        self.compound_layer.process_interaction(input_text, response)
        
        # Calculate processing time
        elapsed = time.time() - start_time
        
        # Log metrics (Wolf's pattern: show evidence)
        metrics = self.compound_layer.get_metrics()
        print(f"[WolfEngine] Processed in {elapsed:.4f}s | Metrics: {metrics}")
        
        return response
    
    def ingest(self, data: Any, data_type: str = "text", importance: float = 1.0):
        """
        Ingest data into Forge
        
        Args:
            data: Any data type
            data_type: Type hint for perception
            importance: Importance weight for resonance
        """
        anchors = self.perception.perceive(data, input_type=data_type)
        self.forge.write_pulse(anchors, importance=importance)
        self.forge.build_chains()
        self.pattern_engine.recognize_patterns()
    
    def query_forge(self, token: str) -> Optional[Dict]:
        """Direct query to Forge"""
        return self.forge.query(token)
    
    def get_stats(self) -> Dict:
        """Get system statistics"""
        return self.compound_layer.get_metrics()


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    print("Shadow Wolf Cognitive Engine - Initializing...")
    
    # Create engine
    wolf = WolfEngine()
    
    # Ingest Wolf's architectural principles
    wolf.ingest("data agnostic architecture with anchors chains and resonance", importance=2.0)
    wolf.ingest("6-1-6 is N-N-N adjustable not fixed dimensions", importance=2.0)
    wolf.ingest("cpu clusters beat gpu farms for heterogeneous data", importance=2.0)
    wolf.ingest("build today not tomorrow reject vaporware", importance=2.0)
    wolf.ingest("ephemeral interface persistent memory compound intelligence", importance=2.0)
    
    print("\nEngine initialized. Testing cognitive patterns...\n")
    
    # Test 1: Question
    print("=== Test 1: Question ===")
    response = wolf.think("what is data agnostic?", input_type="question")
    print(f"Response: {response}\n")
    
    # Test 2: Proposal (should ACCEPT)
    print("=== Test 2: Proposal (CPU cluster) ===")
    response = wolf.think("build distributed cpu cluster for data agnostic processing", input_type="proposal")
    print(f"Response: {response}\n")
    
    # Test 3: Proposal (should REJECT)
    print("=== Test 3: Proposal (quantum) ===")
    response = wolf.think("use quantum computing for future processing", input_type="proposal")
    print(f"Response: {response}\n")
    
    # Test 4: Show stats
    print("=== System Statistics ===")
    stats = wolf.get_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")
    
    print("\nWolf Engine operational. Ready for deployment.")
