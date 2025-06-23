import os
import logging
import subprocess

from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, OperationFailure
from mongoengine import connect as mongoengine_connect
from nethawk.core.config import Config
from mongoengine import connect as mongoengine_connect, disconnect as mongoengine_disconnect

class MongoDBManager:
    def __init__(self):
        self.config = Config()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.INFO)
        self.host = 'mongodb://localhost'
        self.mongodb_config = self.config.get('mongodb') or {}
        self.port = self.mongodb_config.get('port', 27017)
        self.db_name = self.mongodb_config.get('database', 'nethawk')
        self.dbpath = self.mongodb_config.get('path', '/var/lib/mongodb')
        self.mongodb_url = f"{self.host}:{self.port}/{self.db_name}"

    def connect(self):
        """Connect to MongoDB using MongoEngine."""
        try:
            self.ensure_running()
            self.logger.debug(f"Connecting to MongoDB at [bold green]{self.mongodb_url}[/]")

            # Disconnect any existing connections
            mongoengine_disconnect(alias='default')

            mongoengine_connect(
                db=self.db_name,
                host=f"{self.host}:{self.port}",
                alias='default'
            )
            self.logger.debug("MongoEngine connection established.")
        except Exception as e:
            self.logger.error(f"Failed to connect to MongoDB via MongoEngine: {str(e)}")

    def ensure_dbpath_exists(self):
        """Ensure the database path exists."""
        if not os.path.exists(self.dbpath):
            os.makedirs(self.dbpath)
            self.logger.debug(f"Created database path at: {self.dbpath}")
        else:
            self.logger.debug(f"Database path already exists: {self.dbpath}")

    def is_installed(self):
        """Check if MongoDB is installed on the system."""
        try:
            subprocess.run(['mongod', '--version'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except FileNotFoundError:
            self.logger.error("MongoDB is not installed. Do you want to install it? (y/N): ")
            choice = input().strip().lower()

            if choice == 'y':
                command = ['sudo', 'apt-get', 'install', '-y', 'mongodb']
                subprocess.run(command, check=True)
                self.logger.info("MongoDB installed successfully.")
                return True
            else:
                self.logger.error("MongoDB is required but not installed. Exiting.")
                return False

    def start_service(self, new_port=None):
        """Start MongoDB service."""
        self.ensure_dbpath_exists()

        if new_port is not None:
            self.port = new_port

        command = ['mongod', '--dbpath', self.dbpath, '--port', str(self.port)]
        self.logger.debug(f"Starting MongoDB with command: {' '.join(command)}")

        try:
            subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.logger.info(f"MongoDB started at [bold green]{self.host}[/]:[bold cyan]{self.port}[/]")
            return self.port
        
        except Exception as e:
            self.logger.exception(f"Error starting MongoDB: {str(e)}")
            return None

    def get_client(self):
        """Return a raw MongoClient instance."""
        return MongoClient(f"{self.host}:{self.port}", serverSelectionTimeoutMS=2000)

    def ensure_running(self):
        """Ensure MongoDB is running. If not, try to start it."""
        self.logger.debug(f"Checking MongoDB status on port {self.port}...")

        try:
            client = self.get_client()
            client.server_info()  # Attempt to connect
            self.logger.info(f"MongoDB is running at [bold green]{self.host}[/]:[bold cyan]{self.port}[/]")
            return True

        except ServerSelectionTimeoutError:
            self.logger.warning("MongoDB not running. Attempting to start it...")
            started_port = self.start_service()

            if not started_port:
                for new_port in range(self.port + 1, 28000):
                    self.logger.debug(f"Trying port {new_port}...")
                    started_port = self.start_service(new_port)

                    if started_port:
                        self.config.update("mongodb.port", new_port)
                        self.logger.info(f"MongoDB started at {self.host}:{new_port}")
                        break

            if not started_port:
                self.logger.error("Failed to start MongoDB on any available port.")

        except OperationFailure as e:
            self.logger.warning(f"MongoDB might not be running correctly. Error: {str(e)}")
            self.start_service()

        except Exception as e:
            self.logger.error(f"Unexpected MongoDB check error: {str(e)}")


# Entry point for standalone execution
if __name__ == "__main__":
    manager = MongoDBManager()
    if manager.is_installed():
        manager.connect()
        manager.logger.info("MongoDB setup complete and connected.")
    else:
        manager.logger.error("MongoDB setup aborted.")
