# nethawk/cli/nethawk.py
from argparse import Namespace
import asyncio
from functools import partial
import os
import sys
import logging

from pathlib import Path

# from nethawk.services import nmap
from nethawk.cli import banner, loop  # this should be always on top of twisted imports
from nethawk.cli.options import Options
from nethawk.core.config import Config
from nethawk.core.logger import setup_logging

from nethawk.extensions.dispatcher.engine import Dispatcher

from twisted.internet.task import react
from twisted.internet.asyncioreactor import AsyncioSelectorReactor
from twisted.internet.error import ReactorNotRunning
from scrapy.utils.defer import deferred_f_from_coro_f

from nethawk.core.mongodb import MongoDBManager
from nethawk.core.registry import module_registry

@deferred_f_from_coro_f
async def _execute(_main_args: Namespace, reactor: AsyncioSelectorReactor):
    
    config = Config()

    try:

        config.show_config_path()
        
        if _main_args.config:
            config.use(config_path=str(_main_args.config))

        if _main_args.publish:
            config.republish()
            sys.exit()

        if  _main_args.nmap:
            nmap = module_registry.get_module('nmap')

            return await nmap(target=_main_args.target, port=_main_args.ports) #type: ignore

        # Check at least one of the required inputs must be provided
        required_inputs = [_main_args.target, _main_args.ports, _main_args.service, _main_args.module]
        if any(required_inputs):
            await Dispatcher(
                target=_main_args.target, # Target address
                port=_main_args.ports, # Ports to scan
                service=_main_args.service, # Service name
                modules=_main_args.module, # Module to use
            )
    except SystemExit as e:
        pass  # or just return if you don’t want it to exit the whole program

    except asyncio.CancelledError:
        pass

    except Exception as e:
        logging.getLogger().exception(f"Unexpected Error: {e}")
        raise

def main():
    options = Options()

    _main_args = options.main_args()

    # Setup Debugging & Monitoring 
    setup_logging(
        verbose=_main_args.verbose, 
        debug=_main_args.debug
    )

    database = MongoDBManager()
    
    banner.logo()
    
    # Ready the database
    if database.is_installed():
        database.connect()
    else:
        database.logger.error("MongoDB setup aborted.")

    if os.geteuid() != 0: # type: ignore
        logging.getLogger().error("This must be run as root. Please try again with 'sudo'")
        sys.exit()

    try:
        react(partial(_execute, _main_args))

    except KeyboardInterrupt:
        logging.getLogger().error("Interrupt by user. All Pending Tasks will be cancelled.")
        loop.run_until_complete(loop.shutdown_asyncgens())

    except SystemExit as e:
        return e.code
    
    except ReactorNotRunning:
        pass
    
    except Exception as e:
        logging.getLogger().exception(f"Critical error: {e}")
        raise

    finally:
        if not loop.is_closed():
            pending = [t for t in asyncio.all_tasks(loop=loop) if not t.done()]
            for t in pending:
                t.cancel()
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))

            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()

if __name__ == "__main__":
    main()
