"""
Hardware Validation and Fallback Logic for Symbol Reasoning Engine
Provides robust hardware detection and graceful fallback mechanisms
"""

import json
import platform
import subprocess
import sys
from typing import Dict, List, Optional, Tuple
import warnings

class HardwareValidator:
    def __init__(self):
        self.system_info = self.gather_system_info()
        self.gpu_info = self.detect_gpus()
        self.memory_info = self.get_memory_info()
        
    def gather_system_info(self) -> Dict:
        """Gather comprehensive system information"""
        return {
            "platform": platform.platform(),
            "processor": platform.processor(),
            "architecture": platform.architecture(),
            "python_version": platform.python_version(),
            "cpu_count": self.get_cpu_count()
        }
    
    def get_cpu_count(self) -> Dict:
        """Get CPU core information"""
        import os
        return {
            "physical_cores": os.cpu_count(),
            "logical_cores": os.cpu_count()  # Simplified for now
        }
    
    def detect_gpus(self) -> List[Dict]:
        """Detect available GPUs and their capabilities"""
        gpus = []
        
        # Try NVIDIA GPUs first
        nvidia_gpus = self.detect_nvidia_gpus()
        gpus.extend(nvidia_gpus)
        
        # Try AMD GPUs
        amd_gpus = self.detect_amd_gpus()
        gpus.extend(amd_gpus)
        
        return gpus
    
    def detect_nvidia_gpus(self) -> List[Dict]:
        """Detect NVIDIA GPUs using nvidia-smi"""
        gpus = []
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        parts = [p.strip() for p in line.split(',')]
                        if len(parts) >= 3:
                            gpus.append({
                                "vendor": "NVIDIA",
                                "name": parts[0],
                                "memory_mb": int(parts[1]),
                                "driver_version": parts[2],
                                "backend": "cuda",
                                "detected_method": "nvidia-smi"
                            })
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        # Fallback: Try PyTorch CUDA detection
        if not gpus:
            try:
                import torch
                if torch.cuda.is_available():
                    for i in range(torch.cuda.device_count()):
                        props = torch.cuda.get_device_properties(i)
                        gpus.append({
                            "vendor": "NVIDIA",
                            "name": props.name,
                            "memory_mb": props.total_memory // (1024 * 1024),
                            "compute_capability": f"{props.major}.{props.minor}",
                            "backend": "cuda",
                            "detected_method": "pytorch"
                        })
            except ImportError:
                pass
        
        return gpus
    
    def detect_amd_gpus(self) -> List[Dict]:
        """Detect AMD GPUs using rocm-smi or other methods"""
        gpus = []
        
        # Try rocm-smi
        try:
            result = subprocess.run(
                ["rocm-smi", "--showproductname", "--showmeminfo", "vram"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # Parse rocm-smi output (simplified)
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if "GPU" in line and ":" in line:
                        # Basic parsing - would need more sophisticated parsing for real use
                        gpus.append({
                            "vendor": "AMD",
                            "name": "AMD GPU (detected via rocm-smi)",
                            "backend": "rocm",
                            "detected_method": "rocm-smi"
                        })
                        break
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        # Fallback: Try PyTorch ROCm detection
        if not gpus:
            try:
                import torch
                if torch.cuda.is_available():
                    # Check if this is actually ROCm
                    device_name = torch.cuda.get_device_name(0)
                    if any(keyword in device_name.upper() for keyword in ["AMD", "RADEON", "RX"]):
                        gpus.append({
                            "vendor": "AMD",
                            "name": device_name,
                            "backend": "rocm",
                            "detected_method": "pytorch-rocm"
                        })
            except ImportError:
                pass
        
        return gpus
    
    def get_memory_info(self) -> Dict:
        """Get system memory information"""
        try:
            import psutil
            memory = psutil.virtual_memory()
            return {
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "percent_used": memory.percent
            }
        except ImportError:
            # Fallback method
            return {"total_gb": "unknown", "available_gb": "unknown", "percent_used": "unknown"}
    
    def validate_backend_requirements(self, backend: str) -> Tuple[bool, List[str]]:
        """Validate if system meets requirements for specified backend"""
        issues = []
        
        if backend == "cuda":
            return self.validate_cuda_requirements()
        elif backend == "rocm":
            return self.validate_rocm_requirements()
        elif backend == "cpu":
            return self.validate_cpu_requirements()
        else:
            return False, [f"Unknown backend: {backend}"]
    
    def validate_cuda_requirements(self) -> Tuple[bool, List[str]]:
        """Validate CUDA requirements"""
        issues = []
        
        # Check for NVIDIA GPUs
        nvidia_gpus = [gpu for gpu in self.gpu_info if gpu["vendor"] == "NVIDIA"]
        if not nvidia_gpus:
            issues.append("No NVIDIA GPUs detected")
        
        # Check PyTorch CUDA availability
        try:
            import torch
            if not torch.cuda.is_available():
                issues.append("PyTorch CUDA not available")
        except ImportError:
            issues.append("PyTorch not installed")
        
        # Check CUDA driver
        try:
            subprocess.run(["nvidia-smi"], capture_output=True, check=True, timeout=5)
        except (subprocess.CalledProcessError, FileNotFoundError):
            issues.append("NVIDIA drivers not properly installed")
        
        return len(issues) == 0, issues
    
    def validate_rocm_requirements(self) -> Tuple[bool, List[str]]:
        """Validate ROCm requirements"""
        issues = []
        
        # Check for AMD GPUs
        amd_gpus = [gpu for gpu in self.gpu_info if gpu["vendor"] == "AMD"]
        if not amd_gpus:
            issues.append("No AMD GPUs detected")
        
        # Check PyTorch ROCm availability
        try:
            import torch
            if not torch.cuda.is_available():
                issues.append("PyTorch with ROCm not available")
            else:
                # Additional ROCm-specific checks
                device_name = torch.cuda.get_device_name(0)
                if not any(keyword in device_name.upper() for keyword in ["AMD", "RADEON", "RX"]):
                    issues.append("Detected GPU does not appear to be AMD")
        except ImportError:
            issues.append("PyTorch with ROCm not installed")
        
        # Check ROCm installation
        try:
            subprocess.run(["rocm-smi"], capture_output=True, check=True, timeout=5)
        except (subprocess.CalledProcessError, FileNotFoundError):
            issues.append("ROCm not properly installed")
        
        return len(issues) == 0, issues
    
    def validate_cpu_requirements(self) -> Tuple[bool, List[str]]:
        """Validate CPU-only requirements"""
        issues = []
        
        # Check minimum memory (recommend 8GB for lexicon processing)
        if isinstance(self.memory_info.get("total_gb"), (int, float)):
            if self.memory_info["total_gb"] < 8:
                issues.append(f"Low system memory: {self.memory_info['total_gb']}GB (recommend 8GB+)")
        
        # Check CPU cores (recommend 4+ cores for parallel processing)
        cpu_count = self.system_info["cpu_count"]["physical_cores"]
        if cpu_count and cpu_count < 4:
            issues.append(f"Low CPU core count: {cpu_count} (recommend 4+)")
        
        return len(issues) == 0, issues
    
    def get_optimal_backend(self) -> Tuple[str, str]:
        """Determine optimal backend based on available hardware"""
        # Priority: CUDA > ROCm > CPU
        
        cuda_valid, cuda_issues = self.validate_cuda_requirements()
        if cuda_valid:
            return "cuda", "NVIDIA GPU with CUDA support detected"
        
        rocm_valid, rocm_issues = self.validate_rocm_requirements()
        if rocm_valid:
            return "rocm", "AMD GPU with ROCm support detected"
        
        cpu_valid, cpu_issues = self.validate_cpu_requirements()
        if cpu_valid:
            return "cpu", "Using CPU-only processing"
        else:
            return "cpu", f"Using CPU-only processing (with warnings: {', '.join(cpu_issues)})"
    
    def get_performance_estimate(self, backend: str) -> Dict:
        """Estimate performance characteristics for given backend"""
        estimates = {
            "cuda": {
                "symbol_lookup_per_sec": "300M+",
                "tree_traversal_per_sec": "150M+",
                "memory_efficiency": "High",
                "power_consumption": "High"
            },
            "rocm": {
                "symbol_lookup_per_sec": "200M+", 
                "tree_traversal_per_sec": "100M+",
                "memory_efficiency": "High",
                "power_consumption": "High"
            },
            "cpu": {
                "symbol_lookup_per_sec": "20M",
                "tree_traversal_per_sec": "5M", 
                "memory_efficiency": "Medium",
                "power_consumption": "Low"
            }
        }
        
        return estimates.get(backend, estimates["cpu"])
    
    def generate_hardware_report(self) -> str:
        """Generate comprehensive hardware report"""
        report = []
        report.append("🔍 HARDWARE DETECTION REPORT")
        report.append("=" * 50)
        
        # System info
        report.append(f"🖥️  Platform: {self.system_info['platform']}")
        report.append(f"🔧 Processor: {self.system_info['processor']}")
        report.append(f"💾 Memory: {self.memory_info.get('total_gb', 'unknown')}GB total")
        report.append("")
        
        # GPU info
        if self.gpu_info:
            report.append("🎮 DETECTED GPUs:")
            for i, gpu in enumerate(self.gpu_info):
                report.append(f"  {i+1}. {gpu['name']} ({gpu['vendor']})")
                if 'memory_mb' in gpu:
                    report.append(f"     Memory: {gpu['memory_mb']}MB")
                report.append(f"     Backend: {gpu['backend']}")
        else:
            report.append("🎮 No GPUs detected")
        
        report.append("")
        
        # Backend validation
        report.append("✅ BACKEND VALIDATION:")
        for backend in ["cuda", "rocm", "cpu"]:
            valid, issues = self.validate_backend_requirements(backend)
            status = "✅" if valid else "❌"
            report.append(f"  {status} {backend.upper()}: {'Ready' if valid else 'Issues detected'}")
            if issues:
                for issue in issues:
                    report.append(f"     - {issue}")
        
        report.append("")
        
        # Recommendation
        optimal_backend, reason = self.get_optimal_backend()
        report.append(f"🚀 RECOMMENDATION: {optimal_backend.upper()}")
        report.append(f"   Reason: {reason}")
        
        return "\n".join(report)

def main():
    """Main function for command-line usage"""
    validator = HardwareValidator()
    print(validator.generate_hardware_report())

if __name__ == "__main__":
    main()

