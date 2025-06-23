import pytest
import unittest
import asyncio
from unittest.mock import patch, MagicMock
from pathlib import Path

class TestModuleLoading(unittest.TestCase):

    @patch('nethawk.core.registry.module_registry.find_module')
    def test_module_loading(self, mock_find_module):
        """Test that modules can be found and loaded correctly."""
        from nethawk.modules.protocols import Module as BaseModule
        from nethawk.core.registry import module_registry
        
        # Create a mock module class
        class MockModule(BaseModule):
            name = "mock_module"
            description = "Mock module for testing"
            config_key = "mock"
            
            def options(self, parser, config):
                parser.add_argument('--test-arg', type=str, default='default_value')
                return parser
                
            async def run(self, target, port, args):
                pass
        
        # Configure the mock to return our mock module
        mock_find_module.return_value = MockModule
        
        # Test module lookup
        module_class = module_registry.find_module('mock_module')
        
        # Verify module was found
        self.assertEqual(module_class, MockModule)
        
        # Create module instance
        module = module_class(target="example.com", port="80")
        
        # Verify module properties
        self.assertEqual(module.name, "mock_module")
        self.assertEqual(module.description, "Mock module for testing")

class TestDryRunExecution(unittest.IsolatedAsyncioTestCase):
    """Tests for dry-run execution of modules without network requests."""
    
    @patch('mongoengine.connect')
    async def test_module_dry_run_execution(self, mock_mongo_connect):
        from nethawk.modules.protocols import Module as BaseModule
        import argparse
        
        # Create a concrete module class for testing
        class TestModule(BaseModule):
            name = "mock_module"
            description = "Mock module for testing"
            config_key = "mock"
            
            def options(self, parser, config):
                parser.add_argument('--test-arg', type=str, default='default_value')
                return parser
                
            async def run(self, target, port, args):
                pass
    
        # Create module instance
        module = TestModule(target="example.com", port=80)

        # Test argument parsing
        with patch.object(module, '_parse_arguments') as mock_parse:
            mock_parse.return_value = argparse.Namespace(test_arg='default_value')
            args = module.parse_module_args()
            self.assertEqual(args.test_arg, 'default_value')
        
        # Test module execution
        with patch.object(module, 'run') as mock_module_run:
            await module
            
            # Verify run was called with correct parameters
            mock_module_run.assert_called_once_with(target="example.com", port=80, args=args)