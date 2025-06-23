import logging
from . import DispatchHandler, BaseInitMixin
from .strategy import (
    ServiceDiscovery,
    ServiceListeners,
    ServiceModules
)

class Dispatcher(BaseInitMixin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def __await__(self):
        return self.run().__await__()

    async def run(self):
        if self.service is None:
            await self.dispatch(ServiceDiscovery)
            
        elif self.service and not self.modules:
            await self.dispatch(ServiceListeners)

        elif self.service and self.modules:
            await self.dispatch(ServiceModules)

        else:
            raise ValueError("Invalid dispatcher selection")

    async def dispatch(self, dispatcher_cls):
        if not issubclass(dispatcher_cls, DispatchHandler):
            raise TypeError(f"{dispatcher_cls.__name__} is not a subclass of DispatchHandler")

        strategy = dispatcher_cls(
            target=self.target,
            port=self.port,
            service=self.service,
            modules=self.modules,
        )
        
        # logging.info(f'Target:  {self.target}')
        logging.debug(f"Executing '{dispatcher_cls.__name__}' with port={self.port}, service={self.service}, modules={self.modules}")
        await strategy.run()
