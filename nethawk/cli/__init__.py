import asyncio

import nethawk.core.registry
# Bootstrap all service & module registries
import nethawk.services # triggers nethawk/<services/modules>/__init__.py auto-import in services
import nethawk.modules # triggers nethawk/services/__init__.py auto-import in services

import twisted.internet.asyncioreactor # type: ignore
import twisted.internet.asyncioreactor # type: ignore
# Set up new asyncio loop
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# install reactor on a new asyncio loop
twisted.internet.asyncioreactor.install(eventloop=loop)

# Export the loop so main app can use it
__all__ = ["loop"]
