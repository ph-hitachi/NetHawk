import unittest
import asyncio
from unittest.mock import patch, MagicMock
from pathlib import Path

class TestDispatcherExecution(unittest.IsolatedAsyncioTestCase):
    @patch('nethawk.extensions.dispatcher.engine.Dispatcher.dispatch')
    async def test_if_dispatcher_runs_service_modules(self, mock_dispatch):
        """Test that the Dispatcher dispatches to ServiceModules when service and modules are provided."""
        from nethawk.extensions.dispatcher.engine import Dispatcher, ServiceModules
        
        dispatcher = Dispatcher(
            target="example.com",
            port="80",
            service="http",
            modules=["dir"]
        )
        
        await dispatcher.run()
        
        mock_dispatch.assert_called_once_with(ServiceModules)

    @patch('nethawk.extensions.dispatcher.engine.Dispatcher.dispatch')
    async def test_if_dispatcher_runs_service_listeners(self, mock_dispatch):
        """Test that the Dispatcher dispatches to ServiceListeners when only service is provided."""
        from nethawk.extensions.dispatcher.engine import Dispatcher, ServiceListeners
        
        dispatcher = Dispatcher(
            target="example.com",
            port="80",
            service="http",
            modules=None
        )
        
        await dispatcher.run()
        
        mock_dispatch.assert_called_once_with(ServiceListeners)

    @patch('nethawk.extensions.dispatcher.engine.Dispatcher.dispatch')
    async def test_if_dispatcher_runs_service_discovery(self, mock_dispatch):
        """Test that the Dispatcher dispatches to ServiceDiscovery when no service is provided."""
        from nethawk.extensions.dispatcher.engine import Dispatcher, ServiceDiscovery
        
        dispatcher = Dispatcher(
            target="example.com",
            port="80",
            service=None,
            modules=None
        )
        
        await dispatcher.run()
        
        mock_dispatch.assert_called_once_with(ServiceDiscovery)
