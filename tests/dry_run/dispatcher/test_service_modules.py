import asyncio
from email.policy import default
import unittest
from unittest.mock import AsyncMock, MagicMock, patch, call

# Core imports from nethawk project
from nethawk.extensions.dispatcher.strategy.service_discovery import ServiceDiscovery
from nethawk.extensions.dispatcher.strategy.service_listeners import ServiceListeners
from nethawk.extensions.dispatcher.strategy.service_modules import ServiceModules
from nethawk.modules.protocols import Module as ProtocolModule
from nethawk.modules.discovery import Module as DiscoveryModule
from nethawk.services.handler.protocols import ServiceHandler
from nethawk.helper import db as db_helper# import get_database_info_by_ip
from nethawk.core.registry import service_registry, module_registry

# --- Fake Modules for Testing ---
class FakeTechModule(ProtocolModule):
    name = "tech"
    description = "Fake Tech Module"
    config_key = "fake_tech"
    authors = ["Test Author"]
    tags = ["fake"]
    alias = ['tech']

    def options(self, parser, config):
        return parser

    async def run(self, target, port, args):
        pass  # Simulated implementation

class FakeBannerModule(ProtocolModule):
    name = "banner"
    description = "Fake Banner Module"
    config_key = "fake_banner"
    authors = ["Test Author"]
    tags = ["fake"]
    alias = ['banner']

    def options(self, parser, config):
        return parser

    async def run(self, target, port, args):
        pass  # Simulated implementation

class FakeNmapModule(DiscoveryModule):
    name = "nmap"
    description = "Fake Nmap Module"
    config_key = "fake_nmap"
    authors = ["Test Author"]
    tags = ["fake"]
    alias = ['nmap']

    def options(self, parser, config):
        return parser

    async def run(self, target, port, args):
        pass  # Simulated implementation

# --- Fake Service Handlers for Testing ---

class FakeHttpServiceHandler(ServiceHandler):
    name = "http"
    default_port = 8080
    alias = ["https"]

    def _resolve_listener_names(self):
        # HTTP/HTTPS triggers the "tech" module listeners
        return ["tech", 'banner']

class FakeSshServiceHandler(ServiceHandler):
    name = "ssh"

    def _resolve_listener_names(self):
        # SSH triggers the "banner" module listeners
        return ["banner"]

# --- Test Case for ServiceDiscovery ---

class TestServiceModulesDryRun(unittest.IsolatedAsyncioTestCase):

    @patch.object(FakeTechModule, 'run', new_callable=AsyncMock)
    @patch('nethawk.extensions.modules.Base.parse_module_args')
    @patch.object(service_registry, 'registered')
    @patch.object(module_registry, 'registered')
    @patch('mongoengine.connect')
    async def test_if_modules_runs_in_default_port(
        self,
        mock_mongo_connect,
        mock_module_registry,
        mock_service_registry,
        parse_module_args,
        tech_module_run,
    ):
        mock_service_registry.return_value = return_value={
            "http": FakeHttpServiceHandler,
            "ssh": FakeSshServiceHandler,
        }

        mock_module_registry.return_value = return_value={
            "nmap": FakeNmapModule,
            "tech": FakeTechModule,
            "banner": FakeBannerModule,
        }

        # Create a ServiceDiscovery dispatcher instance for the target
        dispatcher = ServiceModules(target="example.com", service="http", modules='tech')

        # Execute the dispatcher run which triggers associated modules
        await dispatcher.run()

        # Verify the tech module runs exactly for HTTP/HTTPS service
        tech_module_run.assert_awaited_once_with(target="example.com", port=8080, args=None)

    @patch.object(FakeTechModule, 'run', new_callable=AsyncMock)
    @patch('nethawk.extensions.modules.Base.parse_module_args')
    @patch.object(service_registry, 'registered')
    @patch.object(module_registry, 'registered')
    @patch('mongoengine.connect')
    async def test_if_modules_runs_in_specific_port(
        self,
        mock_mongo_connect,
        mock_module_registry,
        mock_service_registry,
        parse_module_args,
        tech_module_run,
    ):
        mock_service_registry.return_value = return_value={
            "http": FakeHttpServiceHandler,
            "ssh": FakeSshServiceHandler,
        }

        mock_module_registry.return_value = return_value={
            "nmap": FakeNmapModule,
            "tech": FakeTechModule,
            "banner": FakeBannerModule,
        }

        # Create a ServiceDiscovery dispatcher instance for the target
        dispatcher = ServiceModules(target="example.com", port=8081, service="http", modules='tech')

        # Execute the dispatcher run which triggers associated modules
        await dispatcher.run()

        # Verify the tech module runs exactly for HTTP/HTTPS service
        tech_module_run.assert_awaited_once_with(target="example.com", port=8081, args=None)

    @patch.object(FakeBannerModule, 'run', new_callable=AsyncMock)
    @patch.object(FakeTechModule, 'run', new_callable=AsyncMock)
    @patch('nethawk.extensions.modules.Base.parse_module_args')
    @patch.object(service_registry, 'registered')
    @patch.object(module_registry, 'registered')
    @patch('mongoengine.connect')
    async def test_if_multiple_modules_runs_in_default_port(
        self,
        mock_mongo_connect,
        mock_module_registry,
        mock_service_registry,
        parse_module_args,
        tech_module_run,
        banner_module_run,
    ):
        mock_service_registry.return_value = return_value={
            "http": FakeHttpServiceHandler,
            "ssh": FakeSshServiceHandler,
        }

        mock_module_registry.return_value = return_value={
            "nmap": FakeNmapModule,
            "tech": FakeTechModule,
            "banner": FakeBannerModule,
        }

        # Create a ServiceDiscovery dispatcher instance for the target
        dispatcher = ServiceModules(target="example.com", service="http", modules=['tech', 'banner'])

        # Execute the dispatcher run which triggers associated modules
        await dispatcher.run()

        # Verify the tech module runs exactly for HTTP/HTTPS service
        tech_module_run.assert_awaited_once_with(target="example.com", port=8080, args=None)
        banner_module_run.assert_awaited_once_with(target="example.com", port=8080, args=None)