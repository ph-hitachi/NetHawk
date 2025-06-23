from abc import ABC, abstractmethod
from typing import Optional, Union

class BaseInitMixin(ABC):
    def __init__(
        self, 
        target: str | None = None,
        port: str | int | list[str | int] | None = None,
        service: str | None = None,
        modules: str | list[str] | None = None
    ):
        self.target = target
        self.port = port
        self.service = service
        self.modules = []

        # Normalize input
        if isinstance(modules, str):
            self.modules = modules.split(',') if modules.lower() != 'none' else []
            
        elif isinstance(modules, list):
            self.modules = modules

class DispatchHandler(BaseInitMixin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    @abstractmethod
    async def run(self):
        pass