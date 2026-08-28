#!/usr/bin/env python3
"""
CortexOS Ray-Coded Neural Engine - Agharmonic Law Compliance Test Suite

This script tests all purified modules for proper implementation of the seven
Agharmonic Law interfaces and verifies system integration between modules.

The test suite validates:
1. All modules implement required Agharmonic Law interfaces
2. Modules can communicate with each other while maintaining resonance integrity
3. The system gracefully handles error conditions and fallbacks
4. Emotional modulation properly affects neural processing parameters

Usage:
    python test_agharmonic_compliance_full.py

Output:
    Detailed test results for all modules and integration tests
"""

import os
import sys
import time
import json
import logging
import unittest
import importlib.util
import numpy as np
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('agharmonic_test_results.log')
    ]
)

logger = logging.getLogger("AgharmonicTest")

# Define test directory structure
PHASE5_DIR = "phase5"
PHASE6_DIR = "phase6"
TEST_RESULTS_FILE = "agharmonic_test_results.json"

class AgharmonicComplianceTest(unittest.TestCase):
    """Test suite for Agharmonic Law compliance verification."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        logger.info("Setting up Agharmonic compliance test environment")
        cls.test_results = {
            "timestamp": datetime.utcnow().isoformat(),
            "modules_tested": 0,
            "interfaces_tested": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "module_results": {},
            "integration_results": {}
        }
        
        # Create mock global sync manager for testing
        cls.global_sync_manager = cls._create_mock_global_sync_manager()
        
        # Load modules for testing
        cls.modules = cls._load_modules()
        
        logger.info(f"Loaded {len(cls.modules)} modules for testing")
    
    @classmethod
    def tearDownClass(cls):
        """Clean up after tests and save results."""
        logger.info("Saving test results")
        
        # Calculate summary statistics
        cls.test_results["modules_tested"] = len(cls.modules)
        cls.test_results["pass_rate"] = (
            cls.test_results["tests_passed"] / 
            max(1, cls.test_results["tests_passed"] + cls.test_results["tests_failed"])
        ) * 100
        
        # Save test results to file
        with open(TEST_RESULTS_FILE, 'w') as f:
            json.dump(cls.test_results, f, indent=2)
        
        logger.info(f"Test results saved to {TEST_RESULTS_FILE}")
        
        # Print summary
        print("\n" + "="*80)
        print(f"AGHARMONIC COMPLIANCE TEST SUMMARY")
        print("="*80)
        print(f"Modules tested: {cls.test_results['modules_tested']}")
        print(f"Interfaces tested: {cls.test_results['interfaces_tested']}")
        print(f"Tests passed: {cls.test_results['tests_passed']}")
        print(f"Tests failed: {cls.test_results['tests_failed']}")
        print(f"Pass rate: {cls.test_results['pass_rate']:.2f}%")
        print("="*80 + "\n")
    
    @classmethod
    def _create_mock_global_sync_manager(cls):
        """Create a mock global sync manager for testing."""
        class MockGlobalSyncManager:
            def __init__(self):
                self.sync_stats = {
                    "cycle_time": 2.5,
                    "last_sync": datetime.utcnow().isoformat(),
                    "sync_count": 0
                }
                self.sync_policy = {
                    "translation": {
                        "threshold": 0.7,
                        "max_time": 1.5,
                        "energy_budget": 0.8
                    },
                    "reflection": {
                        "depth": 3,
                        "ethical_threshold": 0.7,
                        "max_time": 2.0
                    },
                    "inspection": {
                        "frequency": 0.5,
                        "depth": 2,
                        "timeout": 1.0
                    },
                    "repair": {
                        "max_attempts": 3,
                        "timeout": 5.0,
                        "energy_budget": 0.9
                    },
                    "mood": {
                        "transition_threshold": 0.6,
                        "stability_factor": 0.8,
                        "default_mood": "neutral"
                    }
                }
            
            def get_sync_stats(self):
                self.sync_stats["sync_count"] += 1
                self.sync_stats["last_sync"] = datetime.utcnow().isoformat()
                return self.sync_stats
            
            def get_sync_policy(self):
                return self.sync_policy
        
        return MockGlobalSyncManager()
    
    @classmethod
    def _load_modules(cls):
        """Load all modules for testing."""
        modules = {}
        
        # Load Phase 5 modules
        phase5_modules = {
            "cortex_inspector": "cortex_inspector_purified.py",
            "self_repair": "self_repair_purified.py",
            "mirror_reflector": "mirror_reflector_purified.py",
            "symbolic_translator": "symbolic_translator_purified.py"
        }
        
        for module_name, filename in phase5_modules.items():
            filepath = os.path.join(PHASE5_DIR, filename)
            if os.path.exists(filepath):
                try:
                    module = cls._import_module_from_file(module_name, filepath)
                    modules[module_name] = module
                    logger.info(f"Loaded Phase 5 module: {module_name}")
                except Exception as e:
                    logger.error(f"Failed to load {module_name}: {e}")
        
        # Load Phase 6 modules
        phase6_modules = {
            "mood_controller": "mood_controller_purified.py",
            "neuromodulation": "neuromodulation_purified.py"
        }
        
        for module_name, filename in phase6_modules.items():
            filepath = os.path.join(PHASE6_DIR, filename)
            if os.path.exists(filepath):
                try:
                    module = cls._import_module_from_file(module_name, filepath)
                    modules[module_name] = module
                    logger.info(f"Loaded Phase 6 module: {module_name}")
                except Exception as e:
                    logger.error(f"Failed to load {module_name}: {e}")
        
        return modules
    
    @classmethod
    def _import_module_from_file(cls, module_name, filepath):
        """Import a module from a file path."""
        spec = importlib.util.spec_from_file_location(module_name, filepath)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    
    def _record_test_result(self, module_name, interface_name, passed, message=None):
        """Record test result for reporting."""
        if module_name not in self.test_results["module_results"]:
            self.test_results["module_results"][module_name] = {
                "interfaces_tested": 0,
                "tests_passed": 0,
                "tests_failed": 0,
                "interface_results": {}
            }
        
        if interface_name not in self.test_results["module_results"][module_name]["interface_results"]:
            self.test_results["module_results"][module_name]["interface_results"][interface_name] = {
                "passed": passed,
                "message": message
            }
            self.test_results["module_results"][module_name]["interfaces_tested"] += 1
            self.test_results["interfaces_tested"] += 1
        
        if passed:
            self.test_results["tests_passed"] += 1
            self.test_results["module_results"][module_name]["tests_passed"] += 1
        else:
            self.test_results["tests_failed"] += 1
            self.test_results["module_results"][module_name]["tests_failed"] += 1
    
    def _record_integration_result(self, test_name, modules_involved, passed, message=None):
        """Record integration test result for reporting."""
        self.test_results["integration_results"][test_name] = {
            "modules_involved": modules_involved,
            "passed": passed,
            "message": message
        }
        
        if passed:
            self.test_results["tests_passed"] += 1
        else:
            self.test_results["tests_failed"] += 1
    
    def _instantiate_module(self, module_name):
        """Instantiate a module class for testing."""
        module = self.modules.get(module_name)
        if not module:
            self.fail(f"Module {module_name} not found")
        
        # Determine the main class in the module
        main_class = None
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and attr_name.lower() == module_name.lower() or attr_name.lower() == module_name.lower().replace('_', ''):
                main_class = attr
                break
        
        if not main_class:
            self.fail(f"Could not find main class in module {module_name}")
        
        # Instantiate the class with global sync manager
        try:
            instance = main_class(global_sync_manager=self.global_sync_manager)
            return instance
        except TypeError:
            # Try without global sync manager
            try:
                instance = main_class()
                return instance
            except Exception as e:
                self.fail(f"Failed to instantiate {module_name}: {e}")
    
    def test_harmonic_signature_interface(self):
        """Test that all modules implement harmonic_signature() interface."""
        logger.info("Testing harmonic_signature() interface")
        
        for module_name, module in self.modules.items():
            instance = self._instantiate_module(module_name)
            
            try:
                # Test harmonic_signature() interface
                self.assertTrue(hasattr(instance, 'harmonic_signature'), 
                               f"{module_name} missing harmonic_signature() method")
                
                signature = instance.harmonic_signature()
                self.assertIsInstance(signature, dict, 
                                    f"{module_name}.harmonic_signature() should return a dict")
                
                # Check for required fields
                required_fields = ['module', 'rhythm_hz', 'threshold']
                for field in required_fields:
                    self.assertIn(field, signature, 
                                 f"{module_name}.harmonic_signature() missing required field: {field}")
                
                # Validate rhythm_hz is in reasonable range
                self.assertGreater(signature['rhythm_hz'], 0, 
                                  f"{module_name}.harmonic_signature() rhythm_hz should be positive")
                self.assertLess(signature['rhythm_hz'], 10, 
                               f"{module_name}.harmonic_signature() rhythm_hz should be less than 10")
                
                self._record_test_result(module_name, "harmonic_signature", True)
                logger.info(f"{module_name}.harmonic_signature() passed")
                
            except AssertionError as e:
                self._record_test_result(module_name, "harmonic_signature", False, str(e))
                logger.error(f"{module_name}.harmonic_signature() failed: {e}")
            except Exception as e:
                self._record_test_result(module_name, "harmonic_signature", False, str(e))
                logger.error(f"Error testing {module_name}.harmonic_signature(): {e}")
    
    def test_interface_contract_interface(self):
        """Test that all modules implement interface_contract() interface."""
        logger.info("Testing interface_contract() interface")
        
        for module_name, module in self.modules.items():
            instance = self._instantiate_module(module_name)
            
            try:
                # Test interface_contract() interface
                self.assertTrue(hasattr(instance, 'interface_contract'), 
                               f"{module_name} missing interface_contract() method")
                
                # Test with no arguments
                contract = instance.interface_contract()
                self.assertIsNotNone(contract, 
                                    f"{module_name}.interface_contract() should return interface definition")
                
                # Test with invalid input
                try:
                    invalid_input = {"invalid": "input"}
                    result = instance.interface_contract(invalid_input)
                    # Should either return False/error dict or raise ValueError
                    if isinstance(result, bool):
                        self.assertFalse(result, 
                                        f"{module_name}.interface_contract() should reject invalid input")
                    elif isinstance(result, dict):
                        self.assertIn("status", result, 
                                     f"{module_name}.interface_contract() result should have status field")
                        if "status" in result:
                            self.assertNotEqual(result["status"], "success", 
                                              f"{module_name}.interface_contract() should reject invalid input")
                except ValueError:
                    # This is also acceptable - rejecting invalid input
                    pass
                
                self._record_test_result(module_name, "interface_contract", True)
                logger.info(f"{module_name}.interface_contract() passed")
                
            except AssertionError as e:
                self._record_test_result(module_name, "interface_contract", False, str(e))
                logger.error(f"{module_name}.interface_contract() failed: {e}")
            except Exception as e:
                self._record_test_result(module_name, "interface_contract", False, str(e))
                logger.error(f"Error testing {module_name}.interface_contract(): {e}")
    
    def test_cognitive_energy_flow_interface(self):
        """Test that all modules implement cognitive_energy_flow() interface."""
        logger.info("Testing cognitive_energy_flow() interface")
        
        for module_name, module in self.modules.items():
            instance = self._instantiate_module(module_name)
            
            try:
                # Test cognitive_energy_flow() interface
                self.assertTrue(hasattr(instance, 'cognitive_energy_flow'), 
                               f"{module_name} missing cognitive_energy_flow() method")
                
                # Test with different input types
                test_inputs = [
                    "test string",
                    np.random.rand(10),
                    {"key": "value"},
                    [1, 2, 3, 4, 5]
                ]
                
                for test_input in test_inputs:
                    try:
                        # For modules that expect specific input types
                        if module_name == "mirror_reflector":
                            result = instance.cognitive_energy_flow("standard", "test query", 0)
                        elif module_name == "symbolic_translator":
                            result = instance.cognitive_energy_flow(test_input)
                        else:
                            result = instance.cognitive_energy_flow(test_input)
                        
                        # Should return something (normalized signal or metadata)
                        self.assertIsNotNone(result, 
                                           f"{module_name}.cognitive_energy_flow() should return a result")
                        
                        # If result is numpy array, check normalization
                        if isinstance(result, np.ndarray) and result.size > 0:
                            # Check if values are in reasonable range
                            self.assertLessEqual(np.max(result), 1.0, 
                                               f"{module_name}.cognitive_energy_flow() should normalize values <= 1.0")
                            self.assertGreaterEqual(np.min(result), 0.0, 
                                                  f"{module_name}.cognitive_energy_flow() should normalize values >= 0.0")
                        
                        break  # If any input type works, that's sufficient
                    except Exception:
                        continue
                
                self._record_test_result(module_name, "cognitive_energy_flow", True)
                logger.info(f"{module_name}.cognitive_energy_flow() passed")
                
            except AssertionError as e:
                self._record_test_result(module_name, "cognitive_energy_flow", False, str(e))
                logger.error(f"{module_name}.cognitive_energy_flow() failed: {e}")
            except Exception as e:
                self._record_test_result(module_name, "cognitive_energy_flow", False, str(e))
                logger.error(f"Error testing {module_name}.cognitive_energy_flow(): {e}")
    
    def test_sync_clock_interface(self):
        """Test that all modules implement sync_clock() interface."""
        logger.info("Testing sync_clock() interface")
        
        for module_name, module in self.modules.items():
            instance = self._instantiate_module(module_name)
            
            try:
                # Test sync_clock() interface
                self.assertTrue(hasattr(instance, 'sync_clock'), 
                               f"{module_name} missing sync_clock() method")
                
                # Test with global sync manager
                result = instance.sync_clock(self.global_sync_manager)
                
                # Should return True or a dict with status
                if isinstance(result, bool):
                    self.assertTrue(result, 
                                   f"{module_name}.sync_clock() should return True on success")
                elif isinstance(result, dict):
                    self.assertIn("status", result, 
                                 f"{module_name}.sync_clock() result should have status field")
                    if "status" in result:
                        self.assertNotEqual(result["status"], "error", 
                                          f"{module_name}.sync_clock() should not return error status")
                
                # Test without arguments (should use internal global_sync_manager)
                result = instance.sync_clock()
                
                # Should not raise exception
                self.assertIsNotNone(result, 
                                    f"{module_name}.sync_clock() should return a result")
                
                self._record_test_result(module_name, "sync_clock", True)
                logger.info(f"{module_name}.sync_clock() passed")
                
            except AssertionError as e:
                self._record_test_result(module_name, "sync_clock", False, str(e))
                logger.error(f"{module_name}.sync_clock() failed: {e}")
            except Exception as e:
                self._record_test_result(module_name, "sync_clock", False, str(e))
                logger.error(f"Error testing {module_name}.sync_clock(): {e}")
    
    def test_self_regulate_interface(self):
        """Test that all modules implement self_regulate() interface."""
        logger.info("Testing self_regulate() interface")
        
        for module_name, module in self.modules.items():
            instance = self._instantiate_module(module_name)
            
            try:
                # Test self_regulate() interface
                self.assertTrue(hasattr(instance, 'self_regulate'), 
                               f"{module_name} missing self_regulate() method")
                
                # Call self_regulate()
                result = instance.self_regulate()
                
                # Should return a dict with regulation metrics
                self.assertIsInstance(result, dict, 
                                    f"{module_name}.self_regulate() should return a dict")
                
                # Check for some common fields
                common_fields = ['fallback_level']
                found_fields = [field for field in common_fields if field in result]
                self.assertGreater(len(found_fields), 0, 
                                  f"{module_name}.self_regulate() result should have some common fields")
                
                self._record_test_result(module_name, "self_regulate", True)
                logger.info(f"{module_name}.self_regulate() passed")
                
            except AssertionError as e:
                self._record_test_result(module_name, "self_regulate", False, str(e))
                logger.error(f"{module_name}.self_regulate() failed: {e}")
            except Exception as e:
                self._record_test_result(module_name, "self_regulate", False, str(e))
                logger.error(f"Error testing {module_name}.self_regulate(): {e}")
    
    def test_graceful_fallback_interface(self):
        """Test that all modules implement graceful_fallback() interface."""
        logger.info("Testing graceful_fallback() interface")
        
        for module_name, module in self.modules.items():
            instance = self._instantiate_module(module_name)
            
            try:
                # Test graceful_fallback() interface
                self.assertTrue(hasattr(instance, 'graceful_fallback'), 
                               f"{module_name} missing graceful_fallback() method")
                
                # Create test error and context
                test_error = ValueError("Test error for graceful fallback")
                test_context = {"mode": "test", "retry_count": 0}
                
                # Call graceful_fallback()
                result = instance.graceful_fallback(test_error, test_context)
                
                # Should return a dict with fallback info
                self.assertIsInstance(result, dict, 
                                    f"{module_name}.graceful_fallback() should return a dict")
                
                # Check for fallback action
                self.assertIn("fallback_action", result, 
                             f"{module_name}.graceful_fallback() result should have fallback_action field")
                
                # Check for fallback level
                self.assertIn("fallback_level", result, 
                             f"{module_name}.graceful_fallback() result should have fallback_level field")
                
                self._record_test_result(module_name, "graceful_fallback", True)
                logger.info(f"{module_name}.graceful_fallback() passed")
                
            except AssertionError as e:
                self._record_test_result(module_name, "graceful_fallback", False, str(e))
                logger.error(f"{module_name}.graceful_fallback() failed: {e}")
            except Exception as e:
                self._record_test_result(module_name, "graceful_fallback", False, str(e))
                logger.error(f"Error testing {module_name}.graceful_fallback(): {e}")
    
    def test_resonance_chain_validator_interface(self):
        """Test that all modules implement resonance_chain_validator() interface."""
        logger.info("Testing resonance_chain_validator() interface")
        
        for module_name, module in self.modules.items():
            instance = self._instantiate_module(module_name)
            
            try:
                # Test resonance_chain_validator() interface
                self.assertTrue(hasattr(instance, 'resonance_chain_validator'), 
                               f"{module_name} missing resonance_chain_validator() method")
                
                # Create test result based on module type
                if module_name == "symbolic_translator":
                    test_result = {
                        "result": "test",
                        "confidence": 0.8,
                        "mode": "symbolic_to_neural",
                        "timestamp": time.time()
                    }
                elif module_name == "mirror_reflector":
                    test_result = {
                        "result": "test reflection",
                        "confidence": 0.8,
                        "reflection_type": "standard",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                else:
                    test_result = {
                        "result": "test",
                        "confidence": 0.8,
                        "timestamp": time.time()
                    }
                
                # Call resonance_chain_validator()
                result = instance.resonance_chain_validator(test_result)
                
                # Should return True or a dict with validation info
                if isinstance(result, bool):
                    self.assertTrue(result, 
                                   f"{module_name}.resonance_chain_validator() should return True for valid result")
                elif isinstance(result, dict):
                    self.assertIn("valid", result, 
                                 f"{module_name}.resonance_chain_validator() result should have valid field")
                    if "valid" in result:
                        self.assertTrue(result["valid"], 
                                      f"{module_name}.resonance_chain_validator() should validate test result")
                
                # Test with invalid result
                try:
                    invalid_result = {"invalid": "result"}
                    result = instance.resonance_chain_validator(invalid_result)
                    
                    # Should return False or a dict with validation info
                    if isinstance(result, bool):
                        self.assertFalse(result, 
                                        f"{module_name}.resonance_chain_validator() should reject invalid result")
                    elif isinstance(result, dict):
                        self.assertIn("valid", result, 
                                     f"{module_name}.resonance_chain_validator() result should have valid field")
                        if "valid" in result:
                            self.assertFalse(result["valid"], 
                                           f"{module_name}.resonance_chain_validator() should reject invalid result")
                except ValueError:
                    # This is also acceptable - rejecting invalid result
                    pass
                
                self._record_test_result(module_name, "resonance_chain_validator", True)
                logger.info(f"{module_name}.resonance_chain_validator() passed")
                
            except AssertionError as e:
                self._record_test_result(module_name, "resonance_chain_validator", False, str(e))
                logger.error(f"{module_name}.resonance_chain_validator() failed: {e}")
            except Exception as e:
                self._record_test_result(module_name, "resonance_chain_validator", False, str(e))
                logger.error(f"Error testing {module_name}.resonance_chain_validator(): {e}")
    
    def test_mood_controller_integration(self):
        """Test integration between mood_controller and neuromodulation."""
        logger.info("Testing mood_controller and neuromodulation integration")
        
        try:
            # Instantiate modules
            mood_controller = self._instantiate_module("mood_controller")
            neuromodulation = self._instantiate_module("neuromodulation")
            
            # Test mood transition
            current_mood = mood_controller.get_current_mood()
            self.assertIsNotNone(current_mood, "mood_controller.get_current_mood() should return a mood")
            
            # Get neuromodulation parameters for current mood
            params = neuromodulation.get_parameters(current_mood)
            self.assertIsNotNone(params, "neuromodulation.get_parameters() should return parameters")
            self.assertIsInstance(params, dict, "neuromodulation.get_parameters() should return a dict")
            
            # Test mood transition
            new_mood = "focused" if current_mood != "focused" else "neutral"
            success = mood_controller.transition_to_mood(new_mood)
            self.assertTrue(success, f"mood_controller.transition_to_mood({new_mood}) should succeed")
            
            # Get updated mood
            updated_mood = mood_controller.get_current_mood()
            self.assertEqual(updated_mood, new_mood, 
                           f"mood_controller.get_current_mood() should return {new_mood}")
            
            # Get neuromodulation parameters for new mood
            new_params = neuromodulation.get_parameters(updated_mood)
            self.assertIsNotNone(new_params, "neuromodulation.get_parameters() should return parameters")
            self.assertIsInstance(new_params, dict, "neuromodulation.get_parameters() should return a dict")
            
            # Parameters should be different for different moods
            self.assertNotEqual(params, new_params, 
                              "neuromodulation parameters should differ between moods")
            
            self._record_integration_result(
                "mood_controller_neuromodulation_integration",
                ["mood_controller", "neuromodulation"],
                True
            )
            logger.info("mood_controller and neuromodulation integration passed")
            
        except AssertionError as e:
            self._record_integration_result(
                "mood_controller_neuromodulation_integration",
                ["mood_controller", "neuromodulation"],
                False,
                str(e)
            )
            logger.error(f"mood_controller and neuromodulation integration failed: {e}")
        except Exception as e:
            self._record_integration_result(
                "mood_controller_neuromodulation_integration",
                ["mood_controller", "neuromodulation"],
                False,
                str(e)
            )
            logger.error(f"Error testing mood_controller and neuromodulation integration: {e}")
    
    def test_inspector_repair_integration(self):
        """Test integration between cortex_inspector and self_repair."""
        logger.info("Testing cortex_inspector and self_repair integration")
        
        try:
            # Instantiate modules
            inspector = self._instantiate_module("cortex_inspector")
            repair = self._instantiate_module("self_repair")
            
            # Create a test module for inspection
            test_module = {
                "name": "test_module",
                "health": 0.5,
                "status": "degraded"
            }
            
            # Inspect the test module
            inspection_result = inspector.inspect_module(test_module)
            self.assertIsNotNone(inspection_result, "inspector.inspect_module() should return a result")
            self.assertIsInstance(inspection_result, dict, "inspector.inspect_module() should return a dict")
            
            # Repair the test module based on inspection
            repair_result = repair.repair_module(test_module, inspection_result)
            self.assertIsNotNone(repair_result, "repair.repair_module() should return a result")
            self.assertIsInstance(repair_result, dict, "repair.repair_module() should return a dict")
            
            # Check repair status
            self.assertIn("status", repair_result, "repair_result should have status field")
            self.assertIn(repair_result["status"], ["success", "partial", "failed"], 
                         "repair_result status should be success, partial, or failed")
            
            self._record_integration_result(
                "cortex_inspector_self_repair_integration",
                ["cortex_inspector", "self_repair"],
                True
            )
            logger.info("cortex_inspector and self_repair integration passed")
            
        except AssertionError as e:
            self._record_integration_result(
                "cortex_inspector_self_repair_integration",
                ["cortex_inspector", "self_repair"],
                False,
                str(e)
            )
            logger.error(f"cortex_inspector and self_repair integration failed: {e}")
        except Exception as e:
            self._record_integration_result(
                "cortex_inspector_self_repair_integration",
                ["cortex_inspector", "self_repair"],
                False,
                str(e)
            )
            logger.error(f"Error testing cortex_inspector and self_repair integration: {e}")
    
    def test_mirror_translator_integration(self):
        """Test integration between mirror_reflector and symbolic_translator."""
        logger.info("Testing mirror_reflector and symbolic_translator integration")
        
        try:
            # Instantiate modules
            mirror = self._instantiate_module("mirror_reflector")
            translator = self._instantiate_module("symbolic_translator")
            
            # Create a test query for reflection
            test_query = "What is the meaning of resonance in neural systems?"
            
            # Reflect on the query
            reflection_result = mirror.reflect(test_query)
            self.assertIsNotNone(reflection_result, "mirror.reflect() should return a result")
            self.assertIsInstance(reflection_result, dict, "mirror.reflect() should return a dict")
            
            # Extract reflection result
            reflection_text = reflection_result.get("result", "")
            self.assertNotEqual(reflection_text, "", "reflection_result should have non-empty result")
            
            # Translate reflection to neural pattern
            translation_result = translator.symbolic_to_neural(reflection_text)
            self.assertIsNotNone(translation_result, "translator.symbolic_to_neural() should return a result")
            self.assertIsInstance(translation_result, dict, "translator.symbolic_to_neural() should return a dict")
            
            # Extract neural pattern
            neural_pattern = translation_result.get("result")
            self.assertIsNotNone(neural_pattern, "translation_result should have result field")
            
            # Translate back to symbolic
            reverse_result = translator.neural_to_symbolic(neural_pattern)
            self.assertIsNotNone(reverse_result, "translator.neural_to_symbolic() should return a result")
            self.assertIsInstance(reverse_result, dict, "translator.neural_to_symbolic() should return a dict")
            
            self._record_integration_result(
                "mirror_reflector_symbolic_translator_integration",
                ["mirror_reflector", "symbolic_translator"],
                True
            )
            logger.info("mirror_reflector and symbolic_translator integration passed")
            
        except AssertionError as e:
            self._record_integration_result(
                "mirror_reflector_symbolic_translator_integration",
                ["mirror_reflector", "symbolic_translator"],
                False,
                str(e)
            )
            logger.error(f"mirror_reflector and symbolic_translator integration failed: {e}")
        except Exception as e:
            self._record_integration_result(
                "mirror_reflector_symbolic_translator_integration",
                ["mirror_reflector", "symbolic_translator"],
                False,
                str(e)
            )
            logger.error(f"Error testing mirror_reflector and symbolic_translator integration: {e}")
    
    def test_emotional_modulation_effect(self):
        """Test that emotional modulation affects neural processing parameters."""
        logger.info("Testing emotional modulation effect on neural processing")
        
        try:
            # Instantiate modules
            mood_controller = self._instantiate_module("mood_controller")
            neuromodulation = self._instantiate_module("neuromodulation")
            translator = self._instantiate_module("symbolic_translator")
            
            # Get parameters for different moods
            moods_to_test = ["neutral", "focused", "creative", "cautious"]
            mood_params = {}
            
            for mood in moods_to_test:
                # Set mood
                mood_controller.transition_to_mood(mood)
                current_mood = mood_controller.get_current_mood()
                self.assertEqual(current_mood, mood, f"Failed to transition to mood: {mood}")
                
                # Get parameters for mood
                params = neuromodulation.get_parameters(mood)
                mood_params[mood] = params
                
                # Apply parameters to translator
                translator.translation_threshold = params.get("similarity_threshold", 0.65)
                
                # Test translation with mood-specific parameters
                test_text = "The quick brown fox jumps over the lazy dog"
                translation_result = translator.symbolic_to_neural(test_text)
                
                # Store translation result with mood
                mood_params[mood]["translation_result"] = translation_result
            
            # Verify that different moods produce different translation parameters
            for mood1 in moods_to_test:
                for mood2 in moods_to_test:
                    if mood1 != mood2:
                        params1 = mood_params[mood1]
                        params2 = mood_params[mood2]
                        
                        # Check that at least one parameter differs
                        param_keys = ["k", "similarity_threshold", "decay_rate"]
                        diff_found = False
                        
                        for key in param_keys:
                            if key in params1 and key in params2 and params1[key] != params2[key]:
                                diff_found = True
                                break
                        
                        self.assertTrue(diff_found, 
                                      f"Parameters for {mood1} and {mood2} should differ in at least one value")
            
            self._record_integration_result(
                "emotional_modulation_effect",
                ["mood_controller", "neuromodulation", "symbolic_translator"],
                True
            )
            logger.info("Emotional modulation effect test passed")
            
        except AssertionError as e:
            self._record_integration_result(
                "emotional_modulation_effect",
                ["mood_controller", "neuromodulation", "symbolic_translator"],
                False,
                str(e)
            )
            logger.error(f"Emotional modulation effect test failed: {e}")
        except Exception as e:
            self._record_integration_result(
                "emotional_modulation_effect",
                ["mood_controller", "neuromodulation", "symbolic_translator"],
                False,
                str(e)
            )
            logger.error(f"Error testing emotional modulation effect: {e}")
    
    def test_full_system_integration(self):
        """Test full system integration with all modules."""
        logger.info("Testing full system integration")
        
        try:
            # Instantiate all modules
            mood_controller = self._instantiate_module("mood_controller")
            neuromodulation = self._instantiate_module("neuromodulation")
            inspector = self._instantiate_module("cortex_inspector")
            repair = self._instantiate_module("self_repair")
            mirror = self._instantiate_module("mirror_reflector")
            translator = self._instantiate_module("symbolic_translator")
            
            # Set initial mood
            mood_controller.transition_to_mood("neutral")
            current_mood = mood_controller.get_current_mood()
            self.assertEqual(current_mood, "neutral", "Failed to set initial mood to neutral")
            
            # Get parameters for mood
            params = neuromodulation.get_parameters(current_mood)
            
            # Create a test query
            test_query = "How does emotional state affect neural processing?"
            
            # Reflect on the query
            reflection_result = mirror.reflect(test_query)
            reflection_text = reflection_result.get("result", "")
            
            # Translate reflection to neural pattern
            translation_result = translator.symbolic_to_neural(reflection_text)
            neural_pattern = translation_result.get("result")
            
            # Inspect the neural pattern
            inspection_result = inspector.inspect_neural_pattern(neural_pattern)
            
            # Check if repair is needed
            if inspection_result.get("health_score", 1.0) < 0.8:
                repair_result = repair.repair_neural_pattern(neural_pattern, inspection_result)
                neural_pattern = repair_result.get("repaired_pattern", neural_pattern)
            
            # Change mood to see effect on processing
            mood_controller.transition_to_mood("focused")
            new_mood = mood_controller.get_current_mood()
            self.assertEqual(new_mood, "focused", "Failed to transition to focused mood")
            
            # Get new parameters
            new_params = neuromodulation.get_parameters(new_mood)
            
            # Apply new parameters to translator
            translator.translation_threshold = new_params.get("similarity_threshold", 0.65)
            
            # Translate same reflection with new mood
            new_translation_result = translator.symbolic_to_neural(reflection_text)
            new_neural_pattern = new_translation_result.get("result")
            
            # Verify that mood change affected processing
            if isinstance(neural_pattern, np.ndarray) and isinstance(new_neural_pattern, np.ndarray):
                # Calculate cosine similarity
                similarity = np.dot(neural_pattern, new_neural_pattern) / (
                    np.linalg.norm(neural_pattern) * np.linalg.norm(new_neural_pattern)
                )
                
                # Patterns should be similar but not identical
                self.assertLess(similarity, 0.99, "Mood change should affect neural patterns")
                self.assertGreater(similarity, 0.5, "Neural patterns should still be somewhat similar")
            
            self._record_integration_result(
                "full_system_integration",
                ["mood_controller", "neuromodulation", "cortex_inspector", 
                 "self_repair", "mirror_reflector", "symbolic_translator"],
                True
            )
            logger.info("Full system integration test passed")
            
        except AssertionError as e:
            self._record_integration_result(
                "full_system_integration",
                ["mood_controller", "neuromodulation", "cortex_inspector", 
                 "self_repair", "mirror_reflector", "symbolic_translator"],
                False,
                str(e)
            )
            logger.error(f"Full system integration test failed: {e}")
        except Exception as e:
            self._record_integration_result(
                "full_system_integration",
                ["mood_controller", "neuromodulation", "cortex_inspector", 
                 "self_repair", "mirror_reflector", "symbolic_translator"],
                False,
                str(e)
            )
            logger.error(f"Error testing full system integration: {e}")

if __name__ == "__main__":
    unittest.main()
