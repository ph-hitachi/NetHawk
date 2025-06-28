from nethawk.core.resolver import Resolver
from nethawk.extensions.modules import Base
from nethawk.extensions.network.service_scanner import ServiceScanner

class Protocol(Base):
    group = "protocols"
    category = "http"

    def __await__(self):
        return self.run(target=self.target, port=self.port).__await__()