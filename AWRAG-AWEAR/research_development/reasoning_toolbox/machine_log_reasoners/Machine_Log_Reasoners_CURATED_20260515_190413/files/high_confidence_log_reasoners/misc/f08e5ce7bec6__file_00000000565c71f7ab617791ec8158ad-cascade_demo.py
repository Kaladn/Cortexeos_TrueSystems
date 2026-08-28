"""
CascadeDemo: Production demonstration of cascade-guided tokenizer
Complete end-to-end example with training and inference
"""

import torch
import json
import logging
from pathlib import Path
from typing import List, Dict, Any

from cascade_tokenizer import CascadeTokenizer
from cascade_model import CascadeModel, CascadeModelConfig
from cascade_trainer import CascadeTrainer, CascadeDataset, TrainingConfig, CascadeDataPreprocessor
from cascade_inference import CascadeInferenceEngine, InferenceConfig

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CascadeSystem:
    """Complete cascade-guided generation system"""
    
    def __init__(self, model_dir: str = None, device: str = 'cuda'):
        self.device = device
        self.model_dir = model_dir
        self.tokenizer = None
        self.model = None
        self.inference_engine = None
        
    def build_from_corpus(self, corpus: List[str], vocab_size: int = 30000,
                         cascade_definitions: Dict[str, Dict] = None) -> None:
        """Build complete system from text corpus"""
        logger.info("🔥 Building Cascade System from Corpus")
        
        # Step 1: Build tokenizer with cascades
        logger.info("Step 1: Building tokenizer with embedded cascades...")
        self.tokenizer = CascadeTokenizer(vocab_size=vocab_size, min_frequency=2)
        
        # Prepare cascade definitions if not provided
        if cascade_definitions is None:
            preprocessor = CascadeDataPreprocessor(self.tokenizer)
            cascade_definitions = preprocessor.prepare_cascade_definitions(corpus[:1000])  # Sample for speed
            logger.info(f"Generated {len(cascade_definitions)} cascade definitions")
        
        # Build vocabulary with cascades
        self.tokenizer.build_vocabulary(corpus, cascade_definitions)
        logger.info(f"Vocabulary built: {len(self.tokenizer.vocabulary.token_to_id)} tokens")
        
        # Step 2: Create model
        logger.info("Step 2: Creating cascade model...")
        model_config = CascadeModelConfig(
            vocab_size=len(self.tokenizer.vocabulary.token_to_id),
            hidden_size=512,  # Smaller for demo
            num_layers=6,     # Smaller for demo
            num_heads=8,
            max_position_embeddings=512
        )
        
        self.model = CascadeModel(model_config, self.tokenizer)
        logger.info(f"Model created with {sum(p.numel() for p in self.model.parameters())} parameters")
        
        # Step 3: Setup inference engine
        self.inference_engine = CascadeInferenceEngine(
            self.model, self.tokenizer, device=self.device
        )
        logger.info("Inference engine ready")
    
    def train(self, train_corpus: List[str], eval_corpus: List[str] = None,
             training_config: TrainingConfig = None) -> Dict[str, Any]:
        """Train the cascade model"""
        logger.info("🔥 Training Cascade Model")
        
        if training_config is None:
            training_config = TrainingConfig(
                batch_size=8,      # Small for demo
                num_epochs=3,      # Quick training
                learning_rate=1e-4,
                save_steps=500,
                eval_steps=250
            )
        
        # Create datasets
        train_dataset = CascadeDataset(train_corpus, self.tokenizer, max_length=256)
        eval_dataset = CascadeDataset(eval_corpus, self.tokenizer, max_length=256) if eval_corpus else None
        
        # Create trainer
        trainer = CascadeTrainer(self.model, self.tokenizer, training_config)
        
        # Train
        training_stats = trainer.train(train_dataset, eval_dataset)
        
        logger.info("Training completed!")
        return training_stats
    
    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate text with cascade guidance"""
        if self.inference_engine is None:
            raise ValueError("System not initialized. Call build_from_corpus() first.")
        
        return self.inference_engine.generate(prompt, **kwargs)
    
    def save(self, save_dir: str) -> None:
        """Save complete system"""
        save_path = Path(save_dir)
        save_path.mkdir(parents=True, exist_ok=True)
        
        # Save tokenizer
        self.tokenizer.save(str(save_path / "tokenizer.pkl"))
        
        # Save model
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'model_config': self.model.config.__dict__
        }, str(save_path / "model.pt"))
        
        logger.info(f"System saved to {save_dir}")
    
    @classmethod
    def load(cls, model_dir: str, device: str = 'cuda') -> 'CascadeSystem':
        """Load complete system"""
        system = cls(model_dir, device)
        
        # Load tokenizer
        system.tokenizer = CascadeTokenizer.load(str(Path(model_dir) / "tokenizer.pkl"))
        
        # Load model
        model_data = torch.load(str(Path(model_dir) / "model.pt"), map_location=device)
        model_config = CascadeModelConfig(**model_data['model_config'])
        system.model = CascadeModel(model_config, system.tokenizer)
        system.model.load_state_dict(model_data['model_state_dict'])
        system.model.to(device)
        
        # Setup inference
        system.inference_engine = CascadeInferenceEngine(
            system.model, system.tokenizer, device=device
        )
        
        logger.info(f"System loaded from {model_dir}")
        return system

def create_demo_corpus() -> List[str]:
    """Create demonstration corpus with diverse content"""
    return [
        "The artificial intelligence system processes natural language with remarkable accuracy.",
        "Machine learning algorithms learn patterns from large datasets to make predictions.",
        "Neural networks consist of interconnected nodes that simulate brain neurons.",
        "Deep learning models can recognize images, understand speech, and generate text.",
        "Natural language processing enables computers to understand human communication.",
        "Computer vision systems can identify objects and analyze visual scenes.",
        "Robotics combines AI with mechanical engineering to create autonomous machines.",
        "Data science involves extracting insights from complex datasets using statistical methods.",
        "Quantum computing promises to solve problems that are intractable for classical computers.",
        "Blockchain technology provides secure and decentralized transaction recording.",
        "The scientific method involves hypothesis formation, experimentation, and analysis.",
        "Research requires careful observation, data collection, and peer review.",
        "Innovation drives technological progress and societal advancement.",
        "Engineering applies scientific principles to design and build practical solutions.",
        "Mathematics provides the foundation for logical reasoning and problem solving.",
        "Physics explores the fundamental laws governing matter and energy.",
        "Chemistry studies the composition and behavior of atoms and molecules.",
        "Biology investigates living organisms and their interactions with the environment.",
        "Psychology examines human behavior, cognition, and mental processes.",
        "Philosophy questions the nature of reality, knowledge, and existence.",
        "The economy involves the production, distribution, and consumption of goods and services.",
        "Markets facilitate trade between buyers and sellers through price mechanisms.",
        "Finance manages money, investments, and financial risk across time.",
        "Business strategy focuses on competitive advantage and value creation.",
        "Entrepreneurship involves identifying opportunities and creating new ventures.",
        "Leadership requires vision, communication, and the ability to inspire others.",
        "Teamwork combines diverse skills and perspectives to achieve common goals.",
        "Communication enables the exchange of ideas and information between people.",
        "Education develops knowledge, skills, and critical thinking abilities.",
        "Learning is a continuous process of acquiring new understanding and capabilities."
    ]

def create_cascade_definitions() -> Dict[str, Dict]:
    """Create demonstration cascade definitions"""
    return {
        "intelligence": {
            "central_concept": "intelligence",
            "input_concepts": ["cognition", "reasoning", "learning", "adaptation", "problem", "analysis"],
            "output_concepts": ["artificial", "system", "algorithm", "decision", "solution", "capability"],
            "weights": [0.9, 0.8, 0.9, 0.7, 0.8, 0.7, 0.9, 0.8, 0.7, 0.8, 0.7, 0.6, 0.8],
            "constraints": {
                "central_intelligence": {
                    "semantic": ["cognitive", "analytical", "computational"],
                    "logical": ["requires_input", "produces_output"]
                }
            }
        },
        "learning": {
            "central_concept": "learning",
            "input_concepts": ["data", "experience", "training", "pattern", "feedback", "iteration"],
            "output_concepts": ["knowledge", "skill", "model", "prediction", "adaptation", "improvement"],
            "weights": [0.9, 0.8, 0.9, 0.8, 0.7, 0.8, 0.9, 0.8, 0.9, 0.8, 0.7, 0.8, 0.7],
            "constraints": {}
        },
        "system": {
            "central_concept": "system",
            "input_concepts": ["component", "input", "process", "structure", "design", "architecture"],
            "output_concepts": ["output", "behavior", "function", "performance", "result", "operation"],
            "weights": [0.8, 0.9, 0.8, 0.7, 0.8, 0.7, 0.9, 0.8, 0.8, 0.7, 0.8, 0.7, 0.6],
            "constraints": {}
        },
        "algorithm": {
            "central_concept": "algorithm",
            "input_concepts": ["logic", "steps", "rules", "computation", "method", "procedure"],
            "output_concepts": ["solution", "result", "optimization", "efficiency", "automation", "processing"],
            "weights": [0.9, 0.8, 0.8, 0.9, 0.7, 0.8, 0.9, 0.8, 0.7, 0.8, 0.7, 0.8, 0.6],
            "constraints": {}
        }
    }

def run_comprehensive_demo():
    """Run comprehensive demonstration of cascade system"""
    logger.info("🔥💥 STARTING COMPREHENSIVE CASCADE DEMO")
    
    # Create demo data
    corpus = create_demo_corpus()
    cascade_definitions = create_cascade_definitions()
    
    # Split corpus for training/evaluation
    train_corpus = corpus[:24]
    eval_corpus = corpus[24:]
    
    # Initialize system
    system = CascadeSystem(device='cpu')  # Use CPU for demo compatibility
    
    # Build system from corpus
    system.build_from_corpus(train_corpus, vocab_size=5000, cascade_definitions=cascade_definitions)
    
    # Quick training (minimal for demo)
    training_config = TrainingConfig(
        batch_size=2,
        num_epochs=1,
        learning_rate=1e-4,
        save_steps=100,
        eval_steps=50,
        output_dir="./demo_output"
    )
    
    logger.info("🔥 Starting training...")
    training_stats = system.train(train_corpus, eval_corpus, training_config)
    
    # Demonstration generations
    test_prompts = [
        "The artificial intelligence",
        "Machine learning algorithms",
        "Neural networks can",
        "Deep learning models",
        "Computer vision systems"
    ]
    
    logger.info("🔥 Generating with cascade guidance...")
    
    for prompt in test_prompts:
        logger.info(f"\nPrompt: '{prompt}'")
        
        # Generate with different configurations
        configs = [
            {"temperature": 0.7, "max_length": 50, "cascade_guidance_strength": 0.8},
            {"temperature": 1.0, "max_length": 50, "cascade_guidance_strength": 0.5},
            {"temperature": 1.2, "max_length": 50, "cascade_guidance_strength": 0.3}
        ]
        
        for i, config in enumerate(configs):
            result = system.generate(prompt, **config)
            
            logger.info(f"Config {i+1}: {result['generated_text']}")
            logger.info(f"  Time: {result['generation_time']:.3f}s")
            
            # Show cascade guidance stats
            steps = result['generation_log'].get('steps', [])
            cascade_guided = sum(1 for s in steps if s.get('cascade_guided', False))
            logger.info(f"  Cascade-guided steps: {cascade_guided}/{len(steps)}")
    
    # Save system
    system.save("./demo_cascade_system")
    
    # Show final statistics
    stats = system.inference_engine.get_statistics()
    logger.info("\n🔥 Final Generation Statistics:")
    for key, value in stats.items():
        logger.info(f"  {key}: {value}")
    
    logger.info("\n🔥💥 DEMO COMPLETED SUCCESSFULLY!")
    logger.info("System saved to './demo_cascade_system'")
    logger.info("Training output in './demo_output'")

def run_quick_inference_demo():
    """Quick inference demonstration without training"""
    logger.info("🔥 QUICK INFERENCE DEMO")
    
    # Create minimal system
    corpus = create_demo_corpus()[:10]  # Just 10 sentences
    cascade_definitions = create_cascade_definitions()
    
    system = CascadeSystem(device='cpu')
    system.build_from_corpus(corpus, vocab_size=1000, cascade_definitions=cascade_definitions)
    
    # Test generation without training (using random weights)
    prompts = [
        "artificial intelligence",
        "machine learning",
        "neural networks"
    ]
    
    for prompt in prompts:
        result = system.generate(prompt, max_length=30, temperature=0.8)
        logger.info(f"Prompt: '{prompt}' -> '{result['generated_text']}'")
        
        # Show reasoning path
        steps = result['generation_log'].get('steps', [])
        for step in steps[:3]:  # Show first 3 steps
            if step.get('reasoning_path'):
                logger.info(f"  Step {step['step']}: {step['token']} (cascade: {step['cascade_guided']})")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Cascade System Demo")
    parser.add_argument("--mode", choices=["full", "quick"], default="quick",
                       help="Demo mode: full (with training) or quick (inference only)")
    parser.add_argument("--device", default="cpu", help="Device to use (cpu/cuda)")
    
    args = parser.parse_args()
    
    if args.mode == "full":
        run_comprehensive_demo()
    else:
        run_quick_inference_demo()
    
    logger.info("🔥💥 CASCADE DEMO COMPLETE - READY FOR PRODUCTION!")

