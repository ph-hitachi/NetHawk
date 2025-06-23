from nethawk.extensions.modules import Base

class Discovery(Base):
    group = "discovery"
    
    def __await__(self):
        self.parse_module_args()
        return self.run(target=self.target, port=self.port, args=self.args).__await__()
