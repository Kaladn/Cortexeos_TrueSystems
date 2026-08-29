"""
CortexOS Temporal Cognition v2.1
Cortex Cube NVMe Module - Persistent voxel memory grid with binary cell structure

This module implements a persistent memory storage system using a voxel grid approach
with binary cell structure for efficient neural memory operations. It provides
write arbitration, memory bloom failsafes, and temporal ledger logging.

Agharmonic Law Compliance:
- Implements harmonic_signature() for frequency compatibility
- Implements interface_contract() for input validation
- Implements cognitive_energy_flow() for signal normalization
- Implements sync_clock() for temporal framework integration
- Implements self_regulate() for stability monitoring
- Implements graceful_fallback() for degradation handling
- Implements resonance_chain_validator() for integrity verification
"""

import os
import numpy as np
import tempfile
import shutil
import json
import time
import logging
import threading
from datetime import datetime
from collections import deque, defaultdict
import zlib
from typing import Dict, List, Tuple, Any, Optional, Union

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BinaryCell:
    """Binary Cell Structure for neural memory storage"""
    
    HEADER_SIZE = 64  # bytes
    MAGIC_BYTES = b'CORTEX21'
    
    def __init__(self, word_id: str = "", token_id: int = 0):
        self.word_id = word_id
        self.token_id = token_id
        self.frequency = 0
        self.tone_signature = 0.5  # neutral tone
        self.before_context = {}  # words that appear before
        self.after_context = {}   # words that appear after
        self.overflow_links = []  # links to overflow blocks
        self.last_accessed = time.time()
        self.creation_time = time.time()
        self.checksum = 0
        
    def add_context(self, word: str, position: str, weight: float = 1.0):
        """Add contextual relationship to the cell"""
        if position == "before":
            if word in self.before_context:
                self.before_context[word] += weight
            else:
                self.before_context[word] = weight
        elif position == "after":
            if word in self.after_context:
                self.after_context[word] += weight
            else:
                self.after_context[word] = weight
        else:
            raise ValueError(f"Invalid position: {position}. Must be 'before' or 'after'")
        
        self.frequency += 1
        self.last_accessed = time.time()
        self._update_checksum()
        
    def _update_checksum(self):
        """Update the checksum for data integrity verification"""
        data = f"{self.word_id}{self.token_id}{self.frequency}{self.tone_signature}"
        data += str(self.before_context) + str(self.after_context)
        self.checksum = zlib.crc32(data.encode())
        
    def validate(self) -> bool:
        """Validate cell integrity using checksum"""
        data = f"{self.word_id}{self.token_id}{self.frequency}{self.tone_signature}"
        data += str(self.before_context) + str(self.after_context)
        return self.checksum == zlib.crc32(data.encode())
        
    def to_dict(self) -> Dict:
        """Convert cell to dictionary for serialization"""
        return {
            "word_id": self.word_id,
            "token_id": self.token_id,
            "frequency": self.frequency,
            "tone_signature": self.tone_signature,
            "before_context": self.before_context,
            "after_context": self.after_context,
            "overflow_links": self.overflow_links,
            "last_accessed": self.last_accessed,
            "creation_time": self.creation_time,
            "checksum": self.checksum
        }
        
    @classmethod
    def from_dict(cls, data: Dict) -> 'BinaryCell':
        """Create cell from dictionary"""
        cell = cls(data["word_id"], data["token_id"])
        cell.frequency = data["frequency"]
        cell.tone_signature = data["tone_signature"]
        cell.before_context = data["before_context"]
        cell.after_context = data["after_context"]
        cell.overflow_links = data["overflow_links"]
        cell.last_accessed = data["last_accessed"]
        cell.creation_time = data["creation_time"]
        cell.checksum = data["checksum"]
        return cell


class WriteArbitrator:
    """Manages write operations to prevent conflicts and ensure data integrity"""
    
    def __init__(self):
        self.write_lock = threading.RLock()
        self.pending_writes = defaultdict(list)
        self.write_history = deque(maxlen=1000)  # Last 1000 write operations
        
    def request_write(self, source_id: str, target_coords: Tuple[int, int, int], 
                     priority: float, data: Any) -> str:
        """Request a write operation, returns operation_id"""
        operation_id = f"write_{time.time()}_{source_id}_{hash(str(target_coords))}"
        
        with self.write_lock:
            self.pending_writes[target_coords].append({
                "operation_id": operation_id,
                "source_id": source_id,
                "priority": priority,
                "timestamp": time.time(),
                "data": data,
                "status": "pending"
            })
        
        return operation_id
    
    def process_writes(self) -> List[Dict]:
        """Process all pending writes based on priority and timestamp"""
        processed = []
        
        with self.write_lock:
            for coords, writes in self.pending_writes.items():
                if not writes:
                    continue
                    
                # Sort by priority (higher first) and timestamp (older first)
                sorted_writes = sorted(writes, key=lambda w: (-w["priority"], w["timestamp"]))
                
                # Select the highest priority write
                selected_write = sorted_writes[0]
                selected_write["status"] = "approved"
                
                # Mark others as rejected due to conflict
                for write in sorted_writes[1:]:
                    write["status"] = "rejected"
                    write["reason"] = "conflict"
                
                processed.extend(sorted_writes)
                
            # Clear processed writes
            self.pending_writes.clear()
            
            # Add to history
            self.write_history.extend(processed)
            
        return processed
    
    def get_write_status(self, operation_id: str) -> Dict:
        """Get status of a specific write operation"""
        for write in self.write_history:
            if write["operation_id"] == operation_id:
                return write
                
        # Check pending writes
        with self.write_lock:
            for writes in self.pending_writes.values():
                for write in writes:
                    if write["operation_id"] == operation_id:
                        return write
        
        return {"status": "unknown", "operation_id": operation_id}


class CortexCubeNVMe:
    """
    Persistent voxel memory grid with binary cell structure for neural memory storage.
    Implements Agharmonic Law compliance for robust memory operations.
    """
    
    def __init__(self, file_path, shape=(64, 64, 64), binary_cell_path=None):
        """
        Initialize the CortexCube with voxel grid and binary cell structure
        
        Args:
            file_path: Path to the numpy array file for voxel grid
            shape: 3D shape of the voxel grid (default: 64x64x64)
            binary_cell_path: Path to store binary cell data (default: derived from file_path)
        """
        self.file_path = file_path
        self.shape = shape
        self.binary_cell_path = binary_cell_path or f"{os.path.splitext(file_path)[0]}_cells.json"
        
        # Initialize voxel grid
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            try:
                self.cube = np.load(file_path, mmap_mode='r+')
                logger.info(f"Loaded CortexCube from {file_path} (mmap_mode='r+')")
            except Exception as e:
                logger.warning(f"Failed to mmap load cube: {e}")
                logger.info("Attempting fallback load without mmap_mode")
                self.cube = np.load(file_path)
        else:
            logger.info(f"Cube file not found or empty. Creating new cube at {file_path}")
            self._create_new_cube()
        
        # Initialize binary cell structure
        self.cells = {}
        self._load_cells()
        
        # Initialize write arbitration
        self.write_arbitrator = WriteArbitrator()
        
        # Initialize temporal ledger
        self.temporal_ledger = deque(maxlen=10000)  # Last 10000 operations
        
        # Initialize monitoring
        self.last_sync = datetime.utcnow()
        self.activation_history = deque(maxlen=1000)
        self.energy_consumption = 0.0
        self.max_energy_per_cycle = 100.0  # Maximum energy allowed per cycle
        
        # Initialize locks
        self.cube_lock = threading.RLock()
        self.cell_lock = threading.RLock()
        
        # Start background tasks
        self._start_background_tasks()
    
    def harmonic_signature(self) -> Dict:
        """
        Return the harmonic signature for frequency compatibility
        
        Returns:
            Dict containing module identifier and frequency parameters
        """
        return {
            'module': 'cortex_cube_nvme',
            'input_frequency_range': [0.3, 1.0],
            'output_frequency': 0.5,
            'resonance_threshold': 0.6,
            'phase_alignment': 0.05
        }
    
    def interface_contract(self, params: Dict) -> bool:
        """
        Validate input parameters against the interface contract
        
        Args:
            params: Dictionary of parameters to validate
            
        Returns:
            True if valid, raises exception otherwise
        """
        if 'operation' not in params:
            raise ValueError("Missing required parameter: 'operation'")
            
        valid_operations = ['activate', 'read', 'write', 'update', 'delete']
        if params['operation'] not in valid_operations:
            raise ValueError(f"Invalid operation: {params['operation']}. Must be one of {valid_operations}")
            
        if params['operation'] in ['activate', 'write', 'update']:
            required = ['coordinates', 'source_id']
            missing = [k for k in required if k not in params]
            if missing:
                raise ValueError(f"Missing required parameters for {params['operation']}: {missing}")
                
            if 'coordinates' in params:
                x, y, z = params['coordinates']
                if not (0 <= x < self.shape[0] and 0 <= y < self.shape[1] and 0 <= z < self.shape[2]):
                    raise ValueError(f"Coordinates out of bounds: {params['coordinates']}")
                    
            if 'priority' in params and not (0 <= params['priority'] <= 1):
                raise ValueError(f"Priority must be between 0 and 1, got {params['priority']}")
                
        return True
    
    def cognitive_energy_flow(self, energy_value: float) -> float:
        """
        Normalize energy value and enforce energy consumption limits
        
        Args:
            energy_value: Raw energy value
            
        Returns:
            Normalized energy value
        """
        # Clamp energy value between 0 and 1
        normalized = max(0.0, min(1.0, energy_value))
        
        # Scale based on current energy consumption
        if self.energy_consumption > self.max_energy_per_cycle * 0.8:
            # Apply throttling when approaching limit
            throttle_factor = 1.0 - (self.energy_consumption / self.max_energy_per_cycle)
            normalized *= max(0.1, throttle_factor)
            
        # Update energy consumption
        self.energy_consumption += normalized
        
        return normalized
    
    def sync_clock(self) -> bool:
        """
        Check if it's time to process maintenance tasks
        
        Returns:
            True if maintenance should be performed
        """
        now = datetime.utcnow()
        delta = (now - self.last_sync).total_seconds()
        
        # Perform maintenance every 30 seconds
        if delta >= 30:
            self.last_sync = now
            return True
            
        return False
    
    def self_regulate(self) -> None:
        """
        Perform self-regulation to maintain system stability
        """
        if not self.sync_clock():
            return
            
        # Process pending writes
        processed_writes = self.write_arbitrator.process_writes()
        for write in processed_writes:
            if write["status"] == "approved":
                try:
                    x, y, z = write["data"]["coordinates"]
                    intensity = write["data"].get("intensity", 1.0)
                    self._apply_activation(x, y, z, intensity, write["source_id"])
                except Exception as e:
                    logger.error(f"Failed to apply approved write: {e}")
                    
        # Reset energy consumption
        self.energy_consumption = 0.0
        
        # Check for memory bloom
        self._check_memory_bloom()
        
        # Flush to disk if needed
        if len(self.temporal_ledger) > 100:  # After 100 operations
            self.flush()
    
    def graceful_fallback(self, error_type: str, context: Dict) -> Dict:
        """
        Implement graceful degradation for error conditions
        
        Args:
            error_type: Type of error encountered
            context: Context information about the error
            
        Returns:
            Result of fallback action
        """
        result = {
            "success": False,
            "fallback_applied": True,
            "original_error": str(context.get("error", "Unknown error")),
            "fallback_type": error_type
        }
        
        if error_type == "write_failure":
            # Try to write to an alternative location
            try:
                coords = context.get("coordinates", (0, 0, 0))
                alt_coords = self._find_alternative_coordinates(coords)
                if alt_coords:
                    intensity = context.get("intensity", 0.5)
                    source_id = context.get("source_id", "fallback")
                    self._apply_activation(alt_coords[0], alt_coords[1], alt_coords[2], 
                                          intensity * 0.8, source_id)
                    result["success"] = True
                    result["alternative_coordinates"] = alt_coords
            except Exception as e:
                result["fallback_error"] = str(e)
                
        elif error_type == "read_failure":
            # Try to read from nearby coordinates
            try:
                coords = context.get("coordinates", (0, 0, 0))
                alt_coords = self._find_alternative_coordinates(coords)
                if alt_coords:
                    value = self.cube[alt_coords]
                    result["success"] = True
                    result["alternative_coordinates"] = alt_coords
                    result["value"] = float(value)
            except Exception as e:
                result["fallback_error"] = str(e)
                
        elif error_type == "cell_corruption":
            # Try to recover or recreate the cell
            try:
                word_id = context.get("word_id", "")
                if word_id:
                    # Create a new cell
                    self.cells[word_id] = BinaryCell(word_id)
                    result["success"] = True
                    result["action"] = "recreated_cell"
            except Exception as e:
                result["fallback_error"] = str(e)
                
        elif error_type == "memory_bloom":
            # Apply memory bloom mitigation
            try:
                self._apply_memory_bloom_mitigation()
                result["success"] = True
                result["action"] = "bloom_mitigation_applied"
            except Exception as e:
                result["fallback_error"] = str(e)
        
        # Log the fallback action
        logger.warning(f"Applied fallback for {error_type}: {result}")
        return result
    
    def resonance_chain_validator(self, chain_data: Dict) -> bool:
        """
        Validate resonance chain integrity
        
        Args:
            chain_data: Data about the resonance chain
            
        Returns:
            True if chain is valid, False otherwise
        """
        # Validate source module
        if "source_module" not in chain_data:
            logger.error("Missing source_module in chain_data")
            return False
            
        # Check if source is in allowed modules
        allowed_sources = ["memory_inserter", "lexicon_seeder", "knowledge_reinforcer"]
        if chain_data["source_module"] not in allowed_sources:
            logger.error(f"Invalid source_module: {chain_data['source_module']}")
            return False
            
        # Validate operation type
        if "operation" not in chain_data:
            logger.error("Missing operation in chain_data")
            return False
            
        # Check temporal consistency
        if "timestamp" in chain_data:
            try:
                op_time = datetime.fromisoformat(chain_data["timestamp"])
                now = datetime.utcnow()
                # Operation should not be from the future
                if op_time > now:
                    logger.error(f"Future timestamp detected: {op_time}")
                    return False
                    
                # Operation should not be too old (1 hour max)
                if (now - op_time).total_seconds() > 3600:
                    logger.warning(f"Stale operation detected: {op_time}")
                    # We allow it but log a warning
            except Exception as e:
                logger.error(f"Invalid timestamp format: {e}")
                return False
        
        # All checks passed
        return True
    
    def activate_voxel(self, x: int, y: int, z: int, intensity: float = 1.0, 
                      source_id: str = "default", priority: float = 0.5) -> Dict:
        """
        Activate a voxel in the memory cube with arbitration
        
        Args:
            x, y, z: Coordinates of the voxel
            intensity: Activation intensity
            source_id: ID of the source module
            priority: Priority of the operation (0-1)
            
        Returns:
            Operation result
        """
        try:
            # Validate parameters
            self.interface_contract({
                'operation': 'activate',
                'coordinates': (x, y, z),
                'source_id': source_id,
                'priority': priority
            })
            
            # Normalize intensity
            normalized_intensity = self.cognitive_energy_flow(intensity)
            
            # Request write operation
            operation_data = {
                "coordinates": (x, y, z),
                "intensity": normalized_intensity,
                "operation": "activate"
            }
            
            operation_id = self.write_arbitrator.request_write(
                source_id, (x, y, z), priority, operation_data
            )
            
            # Log operation
            self._log_operation("activate", {
                "coordinates": (x, y, z),
                "intensity": normalized_intensity,
                "source_id": source_id,
                "priority": priority,
                "operation_id": operation_id
            })
            
            # If high priority, process immediately
            if priority > 0.8:
                self.write_arbitrator.process_writes()
            
            return {
                "success": True,
                "operation_id": operation_id,
                "status": "pending"
            }
            
        except Exception as e:
            logger.error(f"Error activating voxel at ({x}, {y}, {z}): {e}")
            context = {
                "coordinates": (x, y, z),
                "intensity": intensity,
                "source_id": source_id,
                "error": e
            }
            return self.graceful_fallback("write_failure", context)
    
    def read_voxel(self, x: int, y: int, z: int) -> Dict:
        """
        Read a voxel value from the memory cube
        
        Args:
            x, y, z: Coordinates of the voxel
            
        Returns:
            Voxel value and metadata
        """
        try:
            # Validate parameters
            self.interface_contract({
                'operation': 'read',
                'coordinates': (x, y, z)
            })
            
            with self.cube_lock:
                value = float(self.cube[x, y, z])
            
            # Log operation
            self._log_operation("read", {
                "coordinates": (x, y, z),
                "value": value
            })
            
            return {
                "success": True,
                "value": value,
                "coordinates": (x, y, z)
            }
            
        except Exception as e:
            logger.error(f"Error reading voxel at ({x}, {y}, {z}): {e}")
            context = {
                "coordinates": (x, y, z),
                "error": e
            }
            return self.graceful_fallback("read_failure", context)
    
    def add_binary_cell(self, word_id: str, token_id: int = 0) -> Dict:
        """
        Add a new binary cell to the memory structure
        
        Args:
            word_id: Unique identifier for the word
            token_id: Token ID for the word
            
        Returns:
            Operation result
        """
        try:
            with self.cell_lock:
                if word_id in self.cells:
                    return {
                        "success": True,
                        "status": "exists",
                        "word_id": word_id
                    }
                
                self.cells[word_id] = BinaryCell(word_id, token_id)
                
            # Log operation
            self._log_operation("add_cell", {
                "word_id": word_id,
                "token_id": token_id
            })
            
            return {
                "success": True,
                "status": "created",
                "word_id": word_id
            }
            
        except Exception as e:
            logger.error(f"Error adding binary cell for word '{word_id}': {e}")
            context = {
                "word_id": word_id,
                "token_id": token_id,
                "error": e
            }
            return self.graceful_fallback("cell_creation_failure", context)
    
    def update_cell_context(self, word_id: str, context_word: str, 
                           position: str, weight: float = 1.0) -> Dict:
        """
        Update contextual relationship in a binary cell
        
        Args:
            word_id: ID of the target word
            context_word: Word to add to context
            position: 'before' or 'after'
            weight: Relationship weight
            
        Returns:
            Operation result
        """
        try:
            with self.cell_lock:
                if word_id not in self.cells:
                    self.add_binary_cell(word_id)
                
                self.cells[word_id].add_context(context_word, position, weight)
                
            # Log operation
            self._log_operation("update_context", {
                "word_id": word_id,
                "context_word": context_word,
                "position": position,
                "weight": weight
            })
            
            return {
                "success": True,
                "status": "updated",
                "word_id": word_id
            }
            
        except Exception as e:
            logger.error(f"Error updating context for word '{word_id}': {e}")
            context = {
                "word_id": word_id,
                "context_word": context_word,
                "position": position,
                "weight": weight,
                "error": e
            }
            return self.graceful_fallback("context_update_failure", context)
    
    def get_cell(self, word_id: str) -> Dict:
        """
        Retrieve a binary cell by word ID
        
        Args:
            word_id: ID of the word to retrieve
            
        Returns:
            Cell data or error
        """
        try:
            with self.cell_lock:
                if word_id not in self.cells:
                    return {
                        "success": False,
                        "status": "not_found",
                        "word_id": word_id
                    }
                
                cell = self.cells[word_id]
                
                # Validate cell integrity
                if not cell.validate():
                    logger.warning(f"Cell corruption detected for word '{word_id}'")
                    context = {"word_id": word_id, "error": "Cell corruption"}
                    return self.graceful_fallback("cell_corruption", context)
                
                # Update last accessed time
                cell.last_accessed = time.time()
                
            # Log operation
            self._log_operation("get_cell", {
                "word_id": word_id
            })
            
            return {
                "success": True,
                "status": "retrieved",
                "word_id": word_id,
                "cell_data": cell.to_dict()
            }
            
        except Exception as e:
            logger.error(f"Error retrieving cell for word '{word_id}': {e}")
            context = {
                "word_id": word_id,
                "error": e
            }
            return self.graceful_fallback("cell_retrieval_failure", context)
    
    def _create_new_cube(self):
        """Create a new voxel cube"""
        self.cube = np.zeros(self.shape, dtype=np.float32)
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".npy", prefix="cube_tmp_")
        os.close(tmp_fd)
        np.save(tmp_path, self.cube)
        self._flush_to_disk(tmp_path)
        shutil.move(tmp_path, self.file_path)
        logger.info(f"New cube created and saved to {self.file_path}")
    
    def _flush_to_disk(self, path):
        """Flush file to disk"""
        with open(path, "rb") as f:
            os.fsync(f.fileno())
        logger.info(f"Flushed {path} to disk")
    
    def _load_cells(self):
        """Load binary cells from disk"""
        if os.path.exists(self.binary_cell_path) and os.path.getsize(self.binary_cell_path) > 0:
            try:
                with open(self.binary_cell_path, 'r') as f:
                    cell_data = json.load(f)
                    
                for word_id, data in cell_data.items():
                    self.cells[word_id] = BinaryCell.from_dict(data)
                    
                logger.info(f"Loaded {len(self.cells)} binary cells from {self.binary_cell_path}")
            except Exception as e:
                logger.error(f"Failed to load binary cells: {e}")
                logger.info("Creating empty cell structure")
    
    def _save_cells(self):
        """Save binary cells to disk"""
        try:
            # Create temporary file
            tmp_fd, tmp_path = tempfile.mkstemp(suffix=".json", prefix="cells_tmp_")
            os.close(tmp_fd)
            
            # Convert cells to dictionary
            cell_data = {}
            with self.cell_lock:
                for word_id, cell in self.cells.items():
                    cell_data[word_id] = cell.to_dict()
            
            # Write to temporary file
            with open(tmp_path, 'w') as f:
                json.dump(cell_data, f)
                
            # Flush and move
            self._flush_to_disk(tmp_path)
            shutil.move(tmp_path, self.binary_cell_path)
            
            logger.info(f"Saved {len(self.cells)} binary cells to {self.binary_cell_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save binary cells: {e}")
            return False
    
    def _apply_activation(self, x: int, y: int, z: int, intensity: float, source_id: str):
        """Apply activation to a voxel with logging"""
        with self.cube_lock:
            if 0 <= x < self.shape[0] and 0 <= y < self.shape[1] and 0 <= z < self.shape[2]:
                self.cube[x, y, z] += intensity
                
                # Record activation for monitoring
                self.activation_history.append({
                    "coordinates": (x, y, z),
                    "intensity": intensity,
                    "source_id": source_id,
                    "timestamp": datetime.utcnow().isoformat()
                })
            else:
                logger.warning(f"Ignored out-of-bounds activation at ({x}, {y}, {z})")
    
    def _log_operation(self, operation_type: str, details: Dict):
        """Log operation to temporal ledger"""
        entry = {
            "operation": operation_type,
            "timestamp": datetime.utcnow().isoformat(),
            "details": details
        }
        self.temporal_ledger.append(entry)
    
    def _find_alternative_coordinates(self, coords: Tuple[int, int, int]) -> Tuple[int, int, int]:
        """Find alternative coordinates for fallback operations"""
        x, y, z = coords
        
        # Try nearby coordinates
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                for dz in [-1, 0, 1]:
                    if dx == 0 and dy == 0 and dz == 0:
                        continue
                        
                    nx, ny, nz = x + dx, y + dy, z + dz
                    if 0 <= nx < self.shape[0] and 0 <= ny < self.shape[1] and 0 <= nz < self.shape[2]:
                        return (nx, ny, nz)
        
        # If no nearby coordinates work, return a random valid coordinate
        return (
            np.random.randint(0, self.shape[0]),
            np.random.randint(0, self.shape[1]),
            np.random.randint(0, self.shape[2])
        )
    
    def _check_memory_bloom(self):
        """Check for memory bloom conditions"""
        # Calculate average activation intensity
        if not self.activation_history:
            return
            
        recent_activations = list(self.activation_history)[-100:]  # Last 100 activations
        if len(recent_activations) < 10:
            return
            
        avg_intensity = sum(a["intensity"] for a in recent_activations) / len(recent_activations)
        
        # Check for bloom condition (high average intensity)
        if avg_intensity > 0.8:
            logger.warning(f"Memory bloom detected! Average intensity: {avg_intensity}")
            self.graceful_fallback("memory_bloom", {"avg_intensity": avg_intensity})
    
    def _apply_memory_bloom_mitigation(self):
        """Apply mitigation for memory bloom"""
        with self.cube_lock:
            # Apply decay to the entire cube
            self.cube *= 0.9
            
            # Find and cap extremely high values
            high_values = self.cube > 5.0
            if np.any(high_values):
                self.cube[high_values] = 5.0
                logger.info(f"Capped {np.sum(high_values)} high-intensity voxels")
    
    def _start_background_tasks(self):
        """Start background maintenance tasks"""
        def maintenance_task():
            while True:
                try:
                    self.self_regulate()
                except Exception as e:
                    logger.error(f"Error in maintenance task: {e}")
                time.sleep(5)  # Check every 5 seconds
                
        # Start maintenance thread
        threading.Thread(target=maintenance_task, daemon=True).start()
    
    def flush(self):
        """Flush cube and cell data to disk"""
        # Save voxel cube
        try:
            with self.cube_lock:
                tmp_fd, tmp_path = tempfile.mkstemp(suffix=".npy", prefix="cube_flush_")
                os.close(tmp_fd)
                np.save(tmp_path, self.cube)
                self._flush_to_disk(tmp_path)
                shutil.move(tmp_path, self.file_path)
                
            logger.info(f"Cube changes flushed and saved to {self.file_path}")
        except Exception as e:
            logger.error(f"Failed to flush cube: {e}")
        
        # Save binary cells
        self._save_cells()
        
        return {
            "success": True,
            "timestamp": datetime.utcnow().isoformat(),
            "cube_path": self.file_path,
            "cells_path": self.binary_cell_path
        }
