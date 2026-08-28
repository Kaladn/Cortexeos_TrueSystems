#!/usr/bin/env python3
"""
🔧 WINDOWS 11 DEV ENVIRONMENT VERIFICATION SCRIPT
RTX 3070 FTW3 + BO6 Video Analysis Setup Test

Run this script after installing all dependencies to verify everything is working.
"""

import sys
import os
import subprocess
import time
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


def print_header(title):
    """Print a formatted header"""
    print(f"\n{'='*60}")
    print(f"🔍 {title}")
    print('='*60)

def print_success(message):
    """Print success message"""
    print(f"✅ {message}")

def print_error(message):
    """Print error message"""
    print(f"❌ {message}")

def print_warning(message):
    """Print warning message"""
    print(f"⚠️  {message}")

def test_python_version():
    """Test Python version"""
    print_header("PYTHON VERSION CHECK")
    
    version = sys.version_info
    print(f"Python version: {sys.version}")
    
    if version.major == 3 and version.minor == 11:
        print_success("Python 3.11 detected - Perfect!")
    elif version.major == 3 and version.minor == 12:
        print_warning("Python 3.12 detected - May have compatibility issues")
    elif version.major == 3 and version.minor >= 8:
        print_warning(f"Python 3.{version.minor} detected - Should work but 3.11 recommended")
    else:
        print_error(f"Python {version.major}.{version.minor} detected - Upgrade to 3.11 recommended")

def test_pytorch_cuda():
    """Test PyTorch and CUDA"""
    print_header("PYTORCH & CUDA TEST")
    
    try:
        import torch
        print_success(f"PyTorch version: {torch.__version__}")
        
        # Test CUDA availability
        cuda_available = torch.cuda.is_available()
        if cuda_available:
            print_success("CUDA is available!")
            print(f"   CUDA version: {torch.version.cuda}")
            print(f"   GPU count: {torch.cuda.device_count()}")
            
            # Get GPU info
            for i in range(torch.cuda.device_count()):
                gpu_name = torch.cuda.get_device_name(i)
                gpu_memory = torch.cuda.get_device_properties(i).total_memory / 1e9
                print(f"   GPU {i}: {gpu_name} ({gpu_memory:.1f} GB)")
                
                if "RTX 3070" in gpu_name:
                    print_success("RTX 3070 detected - Perfect for BO6 analysis!")
                elif "RTX" in gpu_name:
                    print_success(f"{gpu_name} detected - Great for AI workloads!")
        else:
            print_error("CUDA not available - Check NVIDIA drivers and CUDA installation")
            
    except ImportError:
        print_error("PyTorch not installed")
        print("   Install with: pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118")

def test_computer_vision():
    """Test computer vision libraries"""
    print_header("COMPUTER VISION LIBRARIES")
    
    # Test OpenCV
    try:
        import cv2
        print_success(f"OpenCV version: {cv2.__version__}")
        
        # Test if OpenCV can use GPU
        try:
            gpu_count = cv2.cuda.getCudaEnabledDeviceCount()
            if gpu_count > 0:
                print_success(f"OpenCV CUDA support: {gpu_count} GPU(s) detected")
            else:
                print_warning("OpenCV CUDA support not available")
        except:
            print_warning("OpenCV CUDA support not available")
            
    except ImportError:
        print_error("OpenCV not installed")
        print("   Install with: pip install opencv-python opencv-contrib-python")
    
    # Test YOLO
    try:
        from ultralytics import YOLO
        print_success("YOLO (Ultralytics) available")
        
        # Test YOLO model loading
        try:
            model = YOLO('yolov8n.pt')  # Will download if not present
            print_success("YOLO model loaded successfully")
        except Exception as e:
            print_warning(f"YOLO model loading issue: {e}")
            
    except ImportError:
        print_error("YOLO (Ultralytics) not installed")
        print("   Install with: pip install ultralytics")

def test_audio_processing():
    """Test audio processing libraries"""
    print_header("AUDIO PROCESSING LIBRARIES")
    
    try:
        import librosa
        print_success(f"Librosa available (version: {librosa.__version__})")
    except ImportError:
        print_error("Librosa not installed")
        print("   Install with: pip install librosa")
    
    try:
        import soundfile
        print_success("SoundFile available")
    except ImportError:
        print_error("SoundFile not installed")
        print("   Install with: pip install soundfile")

def test_data_science():
    """Test data science libraries"""
    print_header("DATA SCIENCE LIBRARIES")
    
    packages = {
        'numpy': 'NumPy',
        'pandas': 'Pandas', 
        'matplotlib': 'Matplotlib',
        'seaborn': 'Seaborn',
        'sklearn': 'Scikit-learn'
    }
    
    for pkg, name in packages.items():
        try:
            module = __import__(pkg)
            if hasattr(module, '__version__'):
                print_success(f"{name} version: {module.__version__}")
            else:
                print_success(f"{name} available")
        except ImportError:
            print_error(f"{name} not installed")

def test_utilities():
    """Test utility libraries"""
    print_header("UTILITY LIBRARIES")
    
    packages = {
        'tqdm': 'Progress bars',
        'PIL': 'Pillow (Image processing)',
        'requests': 'HTTP requests',
        'psutil': 'System monitoring'
    }
    
    for pkg, description in packages.items():
        try:
            module = __import__(pkg)
            print_success(f"{description} available")
        except ImportError:
            print_error(f"{description} not installed")

def test_ocr():
    """Test OCR libraries"""
    print_header("OCR LIBRARIES")
    
    try:
        import pytesseract
        print_success("PyTesseract available")
        
        # Test Tesseract executable
        try:
            version = pytesseract.get_tesseract_version()
            print_success(f"Tesseract version: {version}")
        except Exception as e:
            print_error(f"Tesseract executable not found: {e}")
            print("   Download from: https://github.com/UB-Mannheim/tesseract/wiki")
            
    except ImportError:
        print_error("PyTesseract not installed")
        print("   Install with: pip install pytesseract")
    
    try:
        import easyocr
        print_success("EasyOCR available")
    except ImportError:
        print_error("EasyOCR not installed")
        print("   Install with: pip install easyocr")

def test_video_processing():
    """Test video processing libraries"""
    print_header("VIDEO PROCESSING LIBRARIES")
    
    try:
        import moviepy
        print_success("MoviePy available")
    except ImportError:
        print_error("MoviePy not installed")
        print("   Install with: pip install moviepy")
    
    try:
        import imageio
        print_success("ImageIO available")
    except ImportError:
        print_error("ImageIO not installed")
        print("   Install with: pip install imageio")
    
    # Test FFmpeg
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            print_success(f"FFmpeg available: {version_line}")
        else:
            print_error("FFmpeg not working properly")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print_error("FFmpeg not found in PATH")
        print("   Download from: https://www.gyan.dev/ffmpeg/builds/")
        print("   Add C:\\ffmpeg\\bin to PATH")

def test_gpu_computation():
    """Test GPU computation performance"""
    print_header("GPU COMPUTATION TEST")
    
    try:
        import torch
        
        if not torch.cuda.is_available():
            print_error("CUDA not available - skipping GPU test")
            return
        
        print("🚀 Running GPU computation test...")
        
        # Create large matrices
        size = 2000
        device = torch.device('cuda')
        
        print(f"   Creating {size}x{size} matrices on GPU...")
        start_time = time.time()
        
        x = torch.randn(size, size, device=device)
        y = torch.randn(size, size, device=device)
        
        print("   Performing matrix multiplication...")
        z = torch.mm(x, y)
        
        # Synchronize to ensure computation is complete
        torch.cuda.synchronize()
        
        end_time = time.time()
        computation_time = end_time - start_time
        
        print_success(f"GPU computation successful!")
        print(f"   Matrix multiplication time: {computation_time:.3f} seconds")
        print(f"   GPU memory used: {torch.cuda.memory_allocated() / 1e9:.2f} GB")
        
        # Performance assessment
        if computation_time < 0.1:
            print_success("Excellent GPU performance!")
        elif computation_time < 0.5:
            print_success("Good GPU performance!")
        else:
            print_warning("GPU performance seems slow - check drivers")
            
        # Clear GPU memory
        del x, y, z
        torch.cuda.empty_cache()
        
    except Exception as e:
        print_error(f"GPU computation test failed: {e}")

def test_system_info():
    """Display system information"""
    print_header("SYSTEM INFORMATION")
    
    print(f"Operating System: {os.name}")
    print(f"Platform: {sys.platform}")
    
    try:
        import psutil
        print(f"CPU cores: {psutil.cpu_count()}")
        print(f"RAM: {psutil.virtual_memory().total / 1e9:.1f} GB")
        print(f"Available RAM: {psutil.virtual_memory().available / 1e9:.1f} GB")
    except ImportError:
        print("Install psutil for detailed system info")

def main():
    """Main test function"""
    print("🔧 WINDOWS 11 DEV ENVIRONMENT VERIFICATION")
    print("RTX 3070 FTW3 + BO6 Video Analysis Setup")
    print(f"Test started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run all tests
    test_system_info()
    test_python_version()
    test_pytorch_cuda()
    test_computer_vision()
    test_audio_processing()
    test_data_science()
    test_utilities()
    test_ocr()
    test_video_processing()
    test_gpu_computation()
    
    print_header("SETUP VERIFICATION COMPLETE")
    print("🎯 If all tests passed, you're ready for BO6 video analysis!")
    print("🚀 Expected performance with RTX 3070: 200-400+ fps analysis")
    print("\n📁 Next steps:")
    print("   1. Record 3-minute BO6 bot gameplay")
    print("   2. Test video analysis pipeline")
    print("   3. Fine-tune hit detection algorithms")
    
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()

