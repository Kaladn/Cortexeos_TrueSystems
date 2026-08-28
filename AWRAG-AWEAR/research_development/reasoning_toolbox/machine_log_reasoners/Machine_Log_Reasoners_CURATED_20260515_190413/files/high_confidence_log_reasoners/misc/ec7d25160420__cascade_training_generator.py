#!/usr/bin/env python3
"""
🔥💥 ENHANCED CASCADE TOKENIZER TRAINING GENERATOR WITH WATERMARKING 💥🔥

Revolutionary training data generator with built-in cryptographic watermarking
Protects your cascade tokenization IP with invisible ownership markers

Features:
- 6-1-6 Cascade Tokenization
- Multi-level cryptographic watermarking
- Steganographic ownership embedding
- Tamper detection and verification
- Large file processing (any size)
- GPU acceleration support
- Ownership certificates
- IP protection system

Author: Your Revolutionary AI System
"""

import os
import sys
import json
import argparse
import time
from pathlib import Path
from typing import List, Dict, Tuple, Optional

# Import our modules
try:
    from cascade_training_generator import CascadeTrainingGenerator
    from cascade_watermark import create_watermarked_training_data, verify_training_data_ownership, WatermarkConfig
except ImportError as e:
    print(f"❌ Required modules not found: {e}")
    print("Make sure cascade_training_generator.py and cascade_watermark.py are in the same directory")
    sys.exit(1)

class EnhancedCascadeGenerator:
    """Enhanced cascade generator with integrated watermarking"""
    
    def __init__(self, 
                 owner_id: str,
                 security_level: int = 3,
                 context_window: int = 6,
                 chunk_size: int = 10000,
                 use_gpu: bool = True):
        """
        Initialize enhanced generator with watermarking
        
        Args:
            owner_id: Your unique identifier for ownership
            security_level: Watermark security level (1-5)
            context_window: Context window size for cascade tokenization
            chunk_size: Processing chunk size
            use_gpu: Use GPU acceleration if available
        """
        self.owner_id = owner_id
        self.security_level = security_level
        
        # Initialize base generator
        self.generator = CascadeTrainingGenerator(
            context_window=context_window,
            min_word_length=2,
            max_word_length=50,
            use_gpu=use_gpu,
            chunk_size=chunk_size
        )
        
        print(f"🔐 Enhanced Cascade Generator Initialized")
        print(f"   Owner ID: {owner_id}")
        print(f"   Security Level: {security_level}/5")
        print(f"   Watermarking: {'✅ ENABLED' if security_level > 0 else '❌ DISABLED'}")
    
    def process_files_with_watermarking(self, 
                                      input_files: List[str],
                                      output_path: str,
                                      output_format: str = 'json',
                                      generate_certificate: bool = True) -> Dict:
        """
        Process files and generate watermarked training data
        
        Args:
            input_files: List of input file paths
            output_path: Output file path
            output_format: Output format (json, csv, binary)
            generate_certificate: Generate ownership certificate
        
        Returns:
            Processing results with watermark information
        """
        print(f"🚀 Processing {len(input_files)} files with watermarking...")
        start_time = time.time()
        
        # Process all files to generate training data
        all_tokens = []
        
        for file_path in input_files:
            try:
                print(f"📄 Processing: {Path(file_path).name}")
                tokens = list(self.generator.process_file(file_path, output_format))
                all_tokens.extend(tokens)
                print(f"   Generated {len(tokens):,} tokens")
            except Exception as e:
                print(f"❌ Error processing {file_path}: {e}")
                continue
        
        if not all_tokens:
            raise ValueError("No tokens generated from input files")
        
        print(f"✅ Generated {len(all_tokens):,} total tokens")
        
        # Convert tokens to training format
        training_data = [token.to_training_format() for token in all_tokens]
        
        # Apply watermarking if security level > 0
        if self.security_level > 0:
            print(f"🔐 Applying Level {self.security_level} watermarking...")
            watermarked_data, watermark_metadata, certificate = create_watermarked_training_data(
                training_data, 
                self.owner_id, 
                self.security_level
            )
        else:
            watermarked_data = training_data
            watermark_metadata = {}
            certificate = {}
        
        # Prepare final output
        final_output = {
            'metadata': {
                'format': 'cascade_6_1_6_watermarked',
                'total_tokens': len(watermarked_data),
                'context_window': self.generator.context_window,
                'generated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'owner_id': self.owner_id,
                'security_level': self.security_level,
                'processing_time': time.time() - start_time,
                'statistics': self.generator.stats,
                'watermark': watermark_metadata
            },
            'training_data': watermarked_data
        }
        
        # Save training data
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        print(f"💾 Saving watermarked training data...")
        
        if output_format.lower() == 'json':
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(final_output, f, indent=2, ensure_ascii=False)
        
        elif output_format.lower() == 'binary':
            import pickle
            import gzip
            with gzip.open(output_path, 'wb') as f:
                pickle.dump(final_output, f)
        
        # Save ownership certificate
        if generate_certificate and certificate:
            cert_path = output_path.with_suffix('.certificate.json')
            with open(cert_path, 'w', encoding='utf-8') as f:
                json.dump(certificate, f, indent=2, ensure_ascii=False)
            print(f"📜 Ownership certificate saved: {cert_path}")
        
        # Save vocabulary
        vocab_path = output_path.with_suffix('.vocab.json')
        self.generator.generate_vocabulary_file(str(vocab_path))
        
        # Generate verification script
        self._generate_verification_script(output_path.parent)
        
        processing_time = time.time() - start_time
        
        results = {
            'success': True,
            'output_file': str(output_path),
            'certificate_file': str(cert_path) if generate_certificate and certificate else None,
            'vocab_file': str(vocab_path),
            'total_tokens': len(watermarked_data),
            'processing_time': processing_time,
            'watermark_applied': self.security_level > 0,
            'security_level': self.security_level,
            'owner_id': self.owner_id
        }
        
        # Print final statistics
        self._print_final_statistics(results)
        
        return results
    
    def verify_training_data(self, 
                           training_file: str,
                           certificate_file: Optional[str] = None) -> Dict:
        """
        Verify watermarked training data
        
        Args:
            training_file: Path to training data file
            certificate_file: Path to certificate file (optional)
        
        Returns:
            Verification results
        """
        print(f"🔍 Verifying training data: {Path(training_file).name}")
        
        # Load training data
        with open(training_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        training_data = data.get('training_data', [])
        metadata = data.get('metadata', {})
        watermark_metadata = metadata.get('watermark', {})
        
        # Load certificate if provided
        certificate = {}
        if certificate_file and Path(certificate_file).exists():
            with open(certificate_file, 'r', encoding='utf-8') as f:
                certificate = json.load(f)
        
        # Verify watermark
        if watermark_metadata:
            verification_results = verify_training_data_ownership(
                training_data, 
                watermark_metadata, 
                certificate
            )
        else:
            verification_results = {
                'watermark_detected': False,
                'message': 'No watermark metadata found'
            }
        
        return verification_results
    
    def _generate_verification_script(self, output_dir: Path):
        """Generate a verification script for the training data"""
        script_content = f'''#!/usr/bin/env python3
"""
🔍 CASCADE TRAINING DATA VERIFICATION SCRIPT
Generated automatically for your watermarked training data
"""

import json
import sys
from pathlib import Path

# Add current directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent))

try:
    from enhanced_cascade_training_generator import EnhancedCascadeGenerator
except ImportError:
    print("❌ Required modules not found!")
    print("Make sure all cascade generator files are in the same directory")
    sys.exit(1)

def verify_data(training_file, certificate_file=None):
    """Verify training data ownership"""
    generator = EnhancedCascadeGenerator(
        owner_id="{self.owner_id}",
        security_level={self.security_level}
    )
    
    results = generator.verify_training_data(training_file, certificate_file)
    
    print("\\n" + "="*60)
    print("🔍 TRAINING DATA VERIFICATION RESULTS")
    print("="*60)
    
    if results.get('watermark_detected'):
        print("✅ Watermark detected and verified!")
        print(f"   Owner Verified: {{'✅' if results.get('owner_verified') else '❌'}}")
        print(f"   Integrity Verified: {{'✅' if results.get('integrity_verified') else '❌'}}")
        print(f"   Security Level: {{results.get('security_level', 0)}}/5")
        print(f"   Confidence Score: {{results.get('confidence_score', 0):.1%}}")
        
        if results.get('tamper_detected'):
            print("⚠️  WARNING: Tampering detected!")
    else:
        print("❌ No watermark detected or verification failed")
    
    print("="*60)
    return results

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python verify_training_data.py <training_file> [certificate_file]")
        sys.exit(1)
    
    training_file = sys.argv[1]
    certificate_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    verify_data(training_file, certificate_file)
'''
        
        script_path = output_dir / "verify_training_data.py"
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        os.chmod(script_path, 0o755)  # Make executable
        print(f"🔍 Verification script generated: {script_path}")
    
    def _print_final_statistics(self, results: Dict):
        """Print final processing statistics"""
        print("\n" + "="*70)
        print("🔥💥 ENHANCED CASCADE TRAINING GENERATION COMPLETE! 💥🔥")
        print("="*70)
        print(f"📊 Total Tokens Generated: {results['total_tokens']:,}")
        print(f"⏱️  Processing Time: {results['processing_time']:.2f}s")
        print(f"🔐 Watermark Applied: {'✅' if results['watermark_applied'] else '❌'}")
        print(f"🛡️  Security Level: {results['security_level']}/5")
        print(f"👤 Owner ID: {results['owner_id']}")
        print(f"💾 Output File: {results['output_file']}")
        
        if results['certificate_file']:
            print(f"📜 Certificate: {results['certificate_file']}")
        
        print(f"📚 Vocabulary: {results['vocab_file']}")
        
        if results['watermark_applied']:
            print("\n🔐 WATERMARK PROTECTION ACTIVE:")
            print("   • Cryptographic ownership signatures embedded")
            print("   • Steganographic markers in semantic data")
            print("   • Distributed fragment watermarks")
            print("   • Tamper detection enabled")
            print("   • Ownership certificate generated")
        
        print("\n🚀 Your revolutionary cascade tokenization training data is ready!")
        print("   Protected by advanced cryptographic watermarking")
        print("="*70)

def main():
    """Main function for command-line usage"""
    parser = argparse.ArgumentParser(
        description="🔥💥 Enhanced Cascade Tokenizer Training Generator with Watermarking 💥🔥",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python enhanced_cascade_training_generator.py input.txt -o protected_data.json --owner "YourName"
  python enhanced_cascade_training_generator.py *.txt -o data/ --security 5 --owner "Company"
  python enhanced_cascade_training_generator.py large_file.txt --verify protected_data.json
        """
    )
    
    parser.add_argument('input_files', nargs='*', help='Input text files to process')
    parser.add_argument('-o', '--output', help='Output file path')
    parser.add_argument('--owner', required=True, help='Owner identifier for watermarking')
    parser.add_argument('--security', type=int, choices=[0,1,2,3,4,5], default=3,
                       help='Watermark security level (0=none, 5=maximum)')
    parser.add_argument('-f', '--format', choices=['json', 'binary'], default='json',
                       help='Output format')
    parser.add_argument('-w', '--window', type=int, default=6,
                       help='Context window size')
    parser.add_argument('-c', '--chunk-size', type=int, default=10000,
                       help='Processing chunk size')
    parser.add_argument('--gpu', action='store_true',
                       help='Use GPU acceleration')
    parser.add_argument('--verify', help='Verify existing training data file')
    parser.add_argument('--certificate', help='Certificate file for verification')
    
    args = parser.parse_args()
    
    # Initialize enhanced generator
    generator = EnhancedCascadeGenerator(
        owner_id=args.owner,
        security_level=args.security,
        context_window=args.window,
        chunk_size=args.chunk_size,
        use_gpu=args.gpu
    )
    
    # Verification mode
    if args.verify:
        results = generator.verify_training_data(args.verify, args.certificate)
        return
    
    # Generation mode
    if not args.input_files or not args.output:
        parser.error("Input files and output path required for generation mode")
    
    # Expand glob patterns
    from glob import glob
    input_files = []
    for pattern in args.input_files:
        files = glob(pattern)
        if files:
            input_files.extend(files)
        else:
            print(f"⚠️  No files found matching: {pattern}")
    
    if not input_files:
        print("❌ No input files found")
        return
    
    # Process files
    try:
        results = generator.process_files_with_watermarking(
            input_files=input_files,
            output_path=args.output,
            output_format=args.format,
            generate_certificate=True
        )
        
        print(f"\\n🎉 Success! Your watermarked training data is ready.")
        print(f"   Use the verification script to check ownership anytime.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

if __name__ == "__main__":
    main()

