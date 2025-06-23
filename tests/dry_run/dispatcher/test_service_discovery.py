from argparse import Namespace
import logging
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, MagicMock, patch, call

# Core imports from nethawk project
from nethawk.extensions.dispatcher.strategy.service_discovery import ServiceDiscovery
# from nethawk.extensions.modules import Base as BaseModule
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
    alias = ["https"]

    def _resolve_listener_names(self):
        # HTTP/HTTPS triggers the "tech" module listeners
        return ["tech"]

class FakeSshServiceHandler(ServiceHandler):
    name = "ssh"

    def _resolve_listener_names(self):
        # SSH triggers the "banner" module listeners
        return ["banner"]

# --- Test Case for ServiceDiscovery ---

class TestServiceDiscoveryDryRun(unittest.IsolatedAsyncioTestCase):

    @patch.object(FakeBannerModule, 'run', new_callable=AsyncMock)
    @patch.object(FakeTechModule, 'run', new_callable=AsyncMock)
    @patch.object(FakeNmapModule, 'run', new_callable=AsyncMock)
    @patch('nethawk.extensions.modules.Base.parse_module_args')
    @patch("nethawk.extensions.dispatcher.strategy.service_discovery.get_database_info_by_ip")  # Mock DB lookup
    @patch.object(service_registry, 'registered')
    @patch.object(module_registry, 'registered')
    @patch("nethawk.core.resolver.resolve_host")
    @patch('mongoengine.connect')
    async def test_if_nmap_executed_with_correct_target_and_ports(
        self,
        mock_mongo_connect,
        mock_resolver_class,
        mock_module_registry,
        mock_service_registry,
        mock_get_db_info,
        parse_module_args,
        nmap_module_run,
        tech_module_run,
        banner_module_run,
    ):
        # Simulated services returned from a database for the target host
        services = [
            {"name": "http", "port": 80},
            {"name": "http", "port": 8080},
            {"name": "https", "port": 443},
            {"name": "ssh", "port": 22},
        ]

        # Setup mock database response to return the simulated services
        mock_get_db_info.return_value = MagicMock(services=services)
        
        mock_service_registry.return_value = return_value={
            "http": FakeHttpServiceHandler,
            "ssh": FakeSshServiceHandler,
        }

        mock_module_registry.return_value = return_value={
            "nmap": FakeNmapModule,
            "tech": FakeTechModule,
            "banner": FakeBannerModule,
        }
        mock_resolver_class.return_value = SimpleNamespace(**{
            "original": 'example.com',
            "input_type": None,
            "ip": None,
            "hostname": None,
            "icmp_reachable": False,
            "icmp_latency_ms": None,
            "icmp_latency_category": None,
            "os_guess_from_ttl": None,
            "resolved_url": None,
            "port": None,
            "tcp_port_open": None,
            "error": None,
        })

        # Create a ServiceDiscovery dispatcher instance for the target
        dispatcher = ServiceDiscovery(target="example.com")

        # Execute the dispatcher run which triggers associated modules
        await dispatcher.run()

        # Verify that the Nmap module runs once without a specific port (initial scan)
        nmap_module_run.assert_awaited_once_with(target="example.com", port=None, args=None)

    @patch.object(FakeSshServiceHandler, 'run_listeners', new_callable=AsyncMock)
    @patch.object(FakeHttpServiceHandler, 'run_listeners', new_callable=AsyncMock)
    @patch('nethawk.extensions.modules.Base.parse_module_args')
    @patch("nethawk.extensions.dispatcher.strategy.service_discovery.get_database_info_by_ip")  # Mock DB lookup
    @patch.object(service_registry, 'registered')
    @patch.object(module_registry, 'registered')
    @patch("nethawk.core.resolver.resolve_host")
    @patch('mongoengine.connect')
    async def test_if_services_listeners_executed_correctly(
        self,
        mock_mongo_connect,
        mock_resolver_class,
        mock_module_registry,
        mock_service_registry,
        mock_get_db_info,
        parse_module_args,
        http_listeners,
        ssh_listeners,
    ):
        # Simulated services returned from a database for the target host
        services = [
            {"name": "http", "port": 80},
            {"name": "http", "port": 8080},
            {"name": "https", "port": 443},
            {"name": "ssh", "port": 22},
        ]

        # Setup mock database response to return the simulated services
        mock_get_db_info.return_value = MagicMock(services=services)
        
        mock_service_registry.return_value = return_value={
            "http": FakeHttpServiceHandler,
            "ssh": FakeSshServiceHandler,
        }

        mock_module_registry.return_value = return_value={
            "nmap": FakeNmapModule,
            "tech": FakeTechModule,
            "banner": FakeBannerModule,
        }

        mock_resolver_class.return_value = SimpleNamespace(**{
            "original": 'example.com',
            "input_type": None,
            "ip": None,
            "hostname": None,
            "icmp_reachable": False,
            "icmp_latency_ms": None,
            "icmp_latency_category": None,
            "os_guess_from_ttl": None,
            "resolved_url": None,
            "port": None,
            "tcp_port_open": None,
            "error": None,
        })

        # Create a ServiceDiscovery dispatcher instance for the target
        dispatcher = ServiceDiscovery(target="example.com")

        # Execute the dispatcher run which triggers associated modules
        await dispatcher.run()

        # Verify that the Nmap module runs once without a specific port (initial scan)
        ssh_listeners.assert_awaited_once()
        http_listeners.assert_awaited()
        assert http_listeners.await_count == 3

    @patch.object(FakeBannerModule, 'run', new_callable=AsyncMock)
    @patch.object(FakeTechModule, 'run', new_callable=AsyncMock)
    @patch.object(FakeNmapModule, 'run', new_callable=AsyncMock)
    @patch('nethawk.extensions.modules.Base.parse_module_args')
    @patch("nethawk.extensions.dispatcher.strategy.service_discovery.get_database_info_by_ip")  # Mock DB lookup
    @patch.object(service_registry, 'registered')
    @patch.object(module_registry, 'registered')
    @patch("nethawk.core.resolver.resolve_host")
    @patch('mongoengine.connect')
    async def test_if_modules_from_services_and_listeners_executed(
        self,
        mock_mongo_connect,
        mock_resolver_class,
        mock_module_registry,
        mock_service_registry,
        mock_get_db_info,
        parse_module_args,
        nmap_module_run,
        tech_module_run,
        banner_module_run,
    ):
        # Simulated services returned from a database for the target host
        services = [
            {"name": "http", "port": 80},
            {"name": "http", "port": 8080},
            {"name": "https", "port": 443},
            {"name": "ssh", "port": 22},
        ]

        # Setup mock database response to return the simulated services
        mock_get_db_info.return_value = MagicMock(services=services)
        
        mock_service_registry.return_value = return_value={
            "http": FakeHttpServiceHandler,
            "ssh": FakeSshServiceHandler,
        }

        mock_module_registry.return_value = return_value={
            "nmap": FakeNmapModule,
            "tech": FakeTechModule,
            "banner": FakeBannerModule,
        }
        
        mock_resolver_class.return_value = SimpleNamespace(**{
            "original": 'example.com',
            "input_type": None,
            "ip": None,
            "hostname": None,
            "icmp_reachable": False,
            "icmp_latency_ms": None,
            "icmp_latency_category": None,
            "os_guess_from_ttl": None,
            "resolved_url": None,
            "port": None,
            "tcp_port_open": None,
            "error": None,
        })

        # Create a ServiceDiscovery dispatcher instance for the target
        dispatcher = ServiceDiscovery(target="example.com")

        # Execute the dispatcher run which triggers associated modules
        await dispatcher.run()

        # Verify that the Nmap module runs once without a specific port (initial scan)
        nmap_module_run.assert_awaited_once_with(target="example.com", port=None, args=None)

        # Verify the banner module runs once for the SSH service on port 22
        banner_module_run.assert_awaited_once_with(target="example.com", port=22, args=None)

        # Verify the tech module runs exactly three times for HTTP/HTTPS ports
        tech_module_run.assert_has_awaits([
            call(target="example.com", port=80, args=None),
            call(target="example.com", port=8080, args=None),
            call(target="example.com", port=443, args=None),
        ])

        assert tech_module_run.await_count == 3
