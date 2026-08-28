"""
Forest AI - Plugin System
Drop-in extensions for Forest AI
v1.1.0
"""

import importlib.util
import inspect
import json
from pathlib import Path
from typing import Dict, Any, Callable, Optional, List
from dataclasses import dataclass, asdict

@dataclass
class PluginManifest:
    """Plugin metadata"""
    name: str
    version: str
    author: str
    description: str
    capabilities: List[str]
    endpoints: Dict[str, str]  # endpoint_name: handler_function_name
    config_schema: Optional[Dict] = None

class PluginBase:
    """Base class for Forest AI plugins"""
    
    def get_manifest(self) -> PluginManifest:
        """Return plugin manifest - must be implemented"""
        raise NotImplementedError("Plugin must implement get_manifest()")
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize plugin with configuration"""
        return True
    
    def shutdown(self) -> bool:
        """Cleanup on shutdown"""
        return True

class PluginManager:
    """Manages Forest AI plugins"""
    
    def __init__(self, plugins_dir: str = "plugins"):
        self.plugins_dir = Path(plugins_dir)
        self.plugins_dir.mkdir(exist_ok=True)
        
        self.loaded_plugins: Dict[str, PluginBase] = {}
        self.plugin_handlers: Dict[str, Callable] = {}
    
    def discover_plugins(self) -> List[Path]:
        """Discover plugin files in plugins directory"""
        return list(self.plugins_dir.glob("*.py"))
    
    def load_plugin(self, plugin_path: Path, config: Optional[Dict] = None) -> bool:
        """Load a plugin from file"""
        try:
            # Load module
            spec = importlib.util.spec_from_file_location(plugin_path.stem, plugin_path)
            if not spec or not spec.loader:
                return False
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find plugin class (should inherit from PluginBase)
            plugin_class = None
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, PluginBase) and obj != PluginBase:
                    plugin_class = obj
                    break
            
            if not plugin_class:
                print(f"No plugin class found in {plugin_path}")
                return False
            
            # Instantiate plugin
            plugin = plugin_class()
            manifest = plugin.get_manifest()
            
            # Initialize
            if config is None:
                config = {}
            
            if not plugin.initialize(config):
                print(f"Failed to initialize plugin: {manifest.name}")
                return False
            
            # Register handlers
            for endpoint_name, handler_func_name in manifest.endpoints.items():
                handler = getattr(plugin, handler_func_name, None)
                if handler and callable(handler):
                    self.plugin_handlers[f"{manifest.name}/{endpoint_name}"] = handler
            
            # Store plugin
            self.loaded_plugins[manifest.name] = plugin
            
            print(f"Loaded plugin: {manifest.name} v{manifest.version}")
            return True
            
        except Exception as e:
            print(f"Error loading plugin {plugin_path}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def load_all_plugins(self):
        """Load all discovered plugins"""
        plugin_files = self.discover_plugins()
        
        for plugin_file in plugin_files:
            self.load_plugin(plugin_file)
    
    def get_plugin(self, name: str) -> Optional[PluginBase]:
        """Get loaded plugin by name"""
        return self.loaded_plugins.get(name)
    
    def list_plugins(self) -> List[Dict[str, Any]]:
        """List all loaded plugins"""
        plugins_info = []
        
        for name, plugin in self.loaded_plugins.items():
            manifest = plugin.get_manifest()
            plugins_info.append({
                'name': manifest.name,
                'version': manifest.version,
                'author': manifest.author,
                'description': manifest.description,
                'capabilities': manifest.capabilities,
                'endpoints': list(manifest.endpoints.keys())
            })
        
        return plugins_info
    
    def execute_plugin(self, plugin_name: str, endpoint: str, **kwargs) -> Any:
        """Execute a plugin endpoint"""
        handler_key = f"{plugin_name}/{endpoint}"
        handler = self.plugin_handlers.get(handler_key)
        
        if not handler:
            raise ValueError(f"Plugin endpoint not found: {handler_key}")
        
        return handler(**kwargs)
    
    def unload_plugin(self, name: str) -> bool:
        """Unload a plugin"""
        plugin = self.loaded_plugins.get(name)
        if not plugin:
            return False
        
        try:
            plugin.shutdown()
            
            # Remove handlers
            manifest = plugin.get_manifest()
            for endpoint_name in manifest.endpoints.keys():
                handler_key = f"{name}/{endpoint_name}"
                self.plugin_handlers.pop(handler_key, None)
            
            # Remove plugin
            del self.loaded_plugins[name]
            
            print(f"Unloaded plugin: {name}")
            return True
            
        except Exception as e:
            print(f"Error unloading plugin {name}: {e}")
            return False
    
    def shutdown_all(self):
        """Shutdown all plugins"""
        for name in list(self.loaded_plugins.keys()):
            self.unload_plugin(name)

# Example Plugin Template
class ExamplePlugin(PluginBase):
    """Example plugin - copy this to create new plugins"""
    
    def get_manifest(self) -> PluginManifest:
        return PluginManifest(
            name="example_plugin",
            version="1.0.0",
            author="Forest AI",
            description="Example plugin demonstrating the plugin system",
            capabilities=["text_analysis", "token_scoring"],
            endpoints={
                "analyze": "analyze_text",
                "score": "score_token"
            },
            config_schema={
                "threshold": "float",
                "mode": "string"
            }
        )
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize plugin"""
        self.threshold = config.get('threshold', 0.5)
        self.mode = config.get('mode', 'default')
        print(f"Example plugin initialized with threshold={self.threshold}, mode={self.mode}")
        return True
    
    def analyze_text(self, text: str) -> Dict[str, Any]:
        """Example analysis endpoint"""
        return {
            'length': len(text),
            'words': len(text.split()),
            'mode': self.mode
        }
    
    def score_token(self, token: str, occurrences: int) -> float:
        """Example scoring endpoint"""
        base_score = occurrences / 100.0
        return min(base_score, 1.0) if base_score > self.threshold else 0.0
    
    def shutdown(self) -> bool:
        """Cleanup"""
        print("Example plugin shutting down")
        return True

# Save example plugin to file
def create_example_plugin(plugins_dir: str = "plugins"):
    """Create example plugin file"""
    plugins_path = Path(plugins_dir)
    plugins_path.mkdir(exist_ok=True)
    
    example_file = plugins_path / "example_plugin.py"
    
    example_code = '''"""
Example Forest AI Plugin
Copy this file to create your own plugins
"""

from typing import Dict, Any, List
from dataclasses import dataclass
from bridges.forest_plugins import PluginBase, PluginManifest

class ExamplePlugin(PluginBase):
    """Example plugin demonstrating capabilities"""
    
    def get_manifest(self) -> PluginManifest:
        return PluginManifest(
            name="example_plugin",
            version="1.0.0",
            author="Forest AI",
            description="Example plugin showing text analysis",
            capabilities=["text_analysis", "token_scoring"],
            endpoints={
                "analyze": "analyze_text",
                "score": "score_token"
            },
            config_schema={
                "threshold": "float",
                "mode": "string"
            }
        )
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize with config"""
        self.threshold = config.get('threshold', 0.5)
        self.mode = config.get('mode', 'default')
        return True
    
    def analyze_text(self, text: str) -> Dict[str, Any]:
        """Analyze text and return stats"""
        words = text.split()
        return {
            'length': len(text),
            'words': len(words),
            'unique_words': len(set(words)),
            'mode': self.mode
        }
    
    def score_token(self, token: str, occurrences: int) -> float:
        """Score a token based on occurrences"""
        base_score = occurrences / 100.0
        return min(base_score, 1.0) if base_score > self.threshold else 0.0
    
    def shutdown(self) -> bool:
        """Cleanup on shutdown"""
        return True

# Plugin instance (required)
plugin = ExamplePlugin()
'''
    
    example_file.write_text(example_code)
    print(f"Created example plugin: {example_file}")

# Global plugin manager instance
_plugin_manager: Optional[PluginManager] = None

def get_plugin_manager(plugins_dir: str = "plugins") -> PluginManager:
    """Get or create plugin manager instance"""
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager(plugins_dir)
    return _plugin_manager
