from nethawk.core.resolver import Resolver
from nethawk.extensions.modules import Base
from nethawk.extensions.network.service_scanner import ServiceScanner

import asyncio

class Protocol(Base):
    group = "protocols"
    category = "http"

    def __await__(self):
        self.parse_module_args()
        return self.run(target=self.target, port=self.port, args=self.args).__await__()

    def get_service(self):
        s_scanner = ServiceScanner()
        resolver = Resolver(self.target, self.port)

        if resolver.get_error():
            return None

        db, service = s_scanner.scan(
            target=resolver.get_ip(), 
            port=str(resolver.get_port())
        )

        if db is None or service is None:
            return None

        return resolver, db, service
