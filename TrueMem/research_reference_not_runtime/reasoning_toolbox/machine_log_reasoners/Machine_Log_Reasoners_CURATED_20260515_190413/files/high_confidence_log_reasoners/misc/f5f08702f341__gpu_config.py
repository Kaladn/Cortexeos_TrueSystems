"""
GPU Configuration System for Symbol Reasoning Engine
Asks users upfront what GPU they have and configures accordingly
"""

import json
import os
import sys
from pathlib import Path

class GPUConfigurator:
    def __init__(self, config_path="config.json"):
        self.config_path = config_path
        self.supported_backends = {
            "cuda": "NVIDIA GPU with CUDA support",
            "rocm": "AMD GPU with ROCm support", 
            "cpu": "CPU-only processing"
        }
    
    def display_banner(self):
        """Display the system banner"""
        print("──────────────────────────────")
        print("🤖 Symbol Reasoning Engine")
        print("──────────────────────────────")
        print("What GPU do you have?")
        print("1) NVIDIA (CUDA)")
        print("2) AMD (ROCm)")
        print("3) CPU only")
        print("──────────────────────────────")
    
    def ask_gpu_preference(self):
        """Ask user for GPU preference and validate"""
        self.display_banner()
        
        while True:
            try:
                choice = input("> ").strip()
                
                if choice == "1":
                    backend = "cuda"
                    break
                elif choice == "2":
                    backend = "rocm"
                    break
                elif choice == "3":
                    backend = "cpu"
                    break
                else:
                    print("❌ Invalid choice. Please enter 1, 2, or 3.")
                    continue
                    
            except KeyboardInterrupt:
                print("\n👋 Setup cancelled.")
                sys.exit(0)
            except EOFError:
                print("\n❌ Invalid input. Please try again.")
                continue
        
        # Validate hardware capabilities
        validated_backend = self.validate_backend(backend)
        
        # Save configuration
        self.save_config(validated_backend)
        
        print(f"✅ Backend set to {validated_backend.upper()}")
        print(f"📝 Configuration saved to {self.config_path}")
        
        return validated_backend
    
    def validate_backend(self, requested_backend):
        """Validate that requested backend is available"""
        if requested_backend == "cpu":
            return "cpu"
        
        if requested_backend == "cuda":
            if self.check_cuda_available():
                print("🔥 CUDA detected and ready!")
                return "cuda"
            else:
                print("⚠️  CUDA not detected, falling back to CPU.")
                return "cpu"
        
        if requested_backend == "rocm":
            if self.check_rocm_available():
                print("🔥 ROCm detected and ready!")
                return "rocm"
            else:
                print("⚠️  ROCm not detected, falling back to CPU.")
                return "cpu"
        
        return "cpu"
    
    def check_cuda_available(self):
        """Check if CUDA is available"""
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            print("📦 PyTorch not installed. Install with: pip install torch")
            return False
    
    def check_rocm_available(self):
        """Check if ROCm is available"""
        try:
            import torch
            # Check for ROCm-specific indicators
            if torch.cuda.is_available():
                # Additional ROCm detection logic
                device_name = torch.cuda.get_device_name(0)
                if "AMD" in device_name or "Radeon" in device_name:
                    return True
            return False
        except ImportError:
            print("📦 PyTorch with ROCm not installed.")
            print("💡 Install with: pip install torch --index-url https://download.pytorch.org/whl/rocm5.6")
            return False
    
    def save_config(self, backend):
        """Save GPU configuration to file"""
        config = {
            "gpu_backend": backend,
            "backend_description": self.supported_backends[backend],
            "configured_at": self.get_timestamp()
        }
        
        try:
            with open(self.config_path, "w") as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"⚠️  Warning: Could not save config file: {e}")
    
    def load_config(self):
        """Load existing GPU configuration"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r") as f:
                    config = json.load(f)
                return config.get("gpu_backend", None)
            return None
        except Exception as e:
            print(f"⚠️  Warning: Could not load config file: {e}")
            return None
    
    def get_gpu_backend(self, force_reconfigure=False):
        """Get GPU backend, asking user if not configured"""
        if force_reconfigure:
            return self.ask_gpu_preference()
        
        existing_backend = self.load_config()
        if existing_backend:
            print(f"🔧 Using configured backend: {existing_backend.upper()}")
            return existing_backend
        else:
            return self.ask_gpu_preference()
    
    def reconfigure(self):
        """Force reconfiguration of GPU backend"""
        print("🔄 Reconfiguring GPU backend...")
        return self.ask_gpu_preference()
    
    def show_status(self):
        """Show current GPU configuration status"""
        backend = self.load_config()
        if backend:
            print(f"🔧 Current backend: {backend.upper()}")
            print(f"📝 Description: {self.supported_backends[backend]}")
            
            # Show hardware detection status
            if backend == "cuda":
                available = "✅" if self.check_cuda_available() else "❌"
                print(f"🔍 CUDA available: {available}")
            elif backend == "rocm":
                available = "✅" if self.check_rocm_available() else "❌"
                print(f"🔍 ROCm available: {available}")
            else:
                print("🔍 CPU-only mode")
        else:
            print("❌ No GPU configuration found. Run setup first.")
    
    def get_timestamp(self):
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()

def main():
    """Main function for command-line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description="GPU Configuration for Symbol Reasoning Engine")
    parser.add_argument("--reconfigure", action="store_true", help="Force reconfiguration")
    parser.add_argument("--status", action="store_true", help="Show current configuration")
    parser.add_argument("--gpu", choices=["nvidia", "amd", "cpu"], help="Set GPU backend directly")
    
    args = parser.parse_args()
    
    configurator = GPUConfigurator()
    
    if args.status:
        configurator.show_status()
    elif args.reconfigure:
        configurator.reconfigure()
    elif args.gpu:
        # Direct backend setting
        backend_map = {"nvidia": "cuda", "amd": "rocm", "cpu": "cpu"}
        backend = configurator.validate_backend(backend_map[args.gpu])
        configurator.save_config(backend)
        print(f"✅ Backend set to {backend.upper()}")
    else:
        # Normal operation - get or ask for backend
        backend = configurator.get_gpu_backend()
        print(f"🚀 Ready to use {backend.upper()} backend!")

if __name__ == "__main__":
    main()

