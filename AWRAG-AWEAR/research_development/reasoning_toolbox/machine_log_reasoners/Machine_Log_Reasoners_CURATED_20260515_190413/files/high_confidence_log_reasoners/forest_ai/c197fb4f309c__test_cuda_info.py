"""
test_cuda_info.py — Forest AI GPU diagnostic

Run with:
    .\.forestvenv\Scripts\python.exe test_cuda_info.py
"""

import subprocess, sys, platform, torch

print("="*70)
print("🌲 Forest AI CUDA / PyTorch Diagnostic")
print("="*70)

print(f"Python executable : {sys.executable}")
print(f"Python version    : {platform.python_version()}")
print(f"Torch version     : {torch.__version__}")

# ---------------- CUDA visibility ----------------
print("\n🔍 Checking CUDA availability...")
print(f"torch.cuda.is_available() -> {torch.cuda.is_available()}")
print(f"torch.backends.cudnn.enabled -> {torch.backends.cudnn.enabled}")

# ---------------- Device details -----------------
if torch.cuda.is_available():
    print("\n🎮 GPU Devices Detected:")
    for i in range(torch.cuda.device_count()):
        print(f"  [{i}] {torch.cuda.get_device_name(i)}")
        print(f"      Capability  : {torch.cuda.get_device_capability(i)}")
        print(f"      Memory (MB) : {torch.cuda.get_device_properties(i).total_memory / 1e6:.1f}")
    print("\n🔥 Current device:", torch.cuda.current_device())
else:
    print("\n⚠️  No GPU visible to PyTorch — falling back to CPU mode.")

# ---------------- System-level sanity checks ----------------
print("\n🔧 nvidia-smi output:")
try:
    smi = subprocess.run(["nvidia-smi"], capture_output=True, text=True)
    print(smi.stdout.strip() or smi.stderr.strip())
except FileNotFoundError:
    print("nvidia-smi not found in PATH")

print("\n🔧 nvcc --version output:")
try:
    nvcc = subprocess.run(["nvcc", "--version"], capture_output=True, text=True)
    print(nvcc.stdout.strip() or nvcc.stderr.strip())
except FileNotFoundError:
    print("nvcc not found in PATH")

# ---------------- Summary ----------------
print("\n📊 Summary:")
if torch.cuda.is_available():
    dev = torch.cuda.get_device_name(0)
    ver = torch.version.cuda
    print(f"✅ CUDA visible to PyTorch! Device: {dev} | CUDA toolkit: {ver}")
else:
    print("❌ PyTorch build cannot access CUDA — likely CPU-only wheel.")
    print("   Fix: install the CUDA 13-compatible PyTorch wheel once released.")
    print("   Temporary fallback: torch==2.8.0+cu122 (for CUDA 12.2) if driver allows.")

print("="*70)
