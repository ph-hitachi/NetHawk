# nethawk/services/http.py
from nethawk.core.registry import register_service, service_registry
from . import ServiceHandler

@register_service()
class HttpService(ServiceHandler):
    name = 'http'
    alias = ['https']
    group = 'protocols'
    default_port = 80
    description = "HTTP Enumeration"

    def should_run_module(self, module):
        # print(f"should run: {module}")
        return True
    
    async def before_run(self, module):
        pass
        # print(f"before run: {module}")

    async def after_run(self, module, result):
        pass
        # print(f"after run: {module} with {result}")
