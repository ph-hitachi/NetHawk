class ServiceNotFound(Exception):
    """Exception raised when a requested service is not found."""
    def __init__(self, message):
        super().__init__(message)

class ModuleNotFound(Exception):
    """Exception raised when a requested module is not found."""
    def __init__(self, message):
        super().__init__(message)
