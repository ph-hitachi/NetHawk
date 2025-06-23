# 🛠️ DEVELOPER GUIDE — NetHawk

Welcome to the **NetHawk** development guide. This document is for contributors who want to extend, maintain, or improve NetHawk — a modular, service-aware recon framework for pentesters and red teamers.

---

## 🚀 Project Goals

* High-performance, async-driven service enumeration
* Modular & protocol-specific architecture
* Configurable profiles for automation and reproducibility
* Built for real-world offensive scenarios (OSCP-style labs & CTFs)

---

## 🧱 Project Structure Overview

```bash

├── .github/                           # End to end testing and release new version update change log
│   └── workflows/
│   │   ├── test.yml
│   │   └── release.yml

nethawk/
├── cli/                            # CLI entrypoints and user interface
│   ├── __init__.py
│   ├── banner.py
│   ├── dispatcher.py               # Specific Module/Listeners dispatchers
│   ├── options.py                  # Argument parsing logic
│   └── nethawk.py                  # Entrypoint (legacy support or top-level logic)

├── core/                           # Core runtime, async logic, config, execution
│   ├── __init__.py                 # manual loop runtime handler
│   ├── config.py                   # YAML/global settings loader
│   ├── models.py                   # DB/models for persistence
│   ├── loader.py                   # specific module loader/importlib handler
│   ├── logger.py                   # setup logging customization & debuging
│   ├── mongodb.py                  # Database structure & database handler
│   ├── registry.py                 # Registry are responsible to register 
│   ├── resolver.py                 # Domain name resolver
│   ├── utils.py                    # Utilities

├── data/                           # Config files and runtime data
│   ├── profiles/                   # Profile workflows
│   │   └── ....
│   └── config.yaml

├── _internal_/                           # Internal dependencies used by modules
│   ├── __init__.py
│   ├── dispatcher/
│   │   ├── __init__.py
│   │   ├── constants.py
│   │   ├── dispatch.py
│   │   └── utils.py
│   ├── domain_resolver/
│   │   ├── __init__.py
│   │   ├── constants.py
│   │   ├── resolver.py
│   │   └── utils.py
│   ├── fuzzer/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── dir.py
│   │   ├── fuzz_engine.py          # Renamed from fuzz.py to avoid naming clash
│   │   ├── utils.py
│   │   └── vhost.py
│   ├── crawler/
│   │   ├── __init__.py
│   │   ├── web.py
│   └── network/                    # Nmap Network Port Scanner for service identity
│       ├── __init__.py
│       ├── scanner.py              # 
│       └── utils.py

├── modules/                       # Protocol-based modules, user-facing logic
│   ├── __init__.py
│   ├── base.py                     # based modules class
│   ├── http/                       # HTTP-specific modules and service logic
│   │   ├── __init__.py             # defines `HTTPService` and `modules()`
│   │   ├── robots.py               # contains RobotsTxt class + run()
│   │   ├── crawler.py
│   │   ├── tech.py
│   │   └── ...
│   └── ...                         # Future protocols like ssh/, ftp/, smb/
├── services/                       # Protocol-based services responsible to list, show, dispatch listeners or modules
│   ├── http.py
│   ├── smb.py
│   ├── ftp.py

├── docs/                           # Documentation and manpages
│   └── man/
│   │    └── nethawk.1
│   └── gitbook/

├── tests/                          # Test cases
│   └── test_nethawk.py

# Project Root
├── Dockerfile
├── Makefile
├── poetry.lock
├── pyproject.toml
├── README.md

```


```bash
nethawk/
├── cli/            # CLI entrypoints and dispatch logic
├── core/           # Runtime, DB, config, and async engine
├── data/           # Config files and profile definitions
├── libs/           # Internal libraries used by services
├── services/       # Protocol-specific service modules
├── tests/          # Unit and integration tests
docs/               # Documentation (e.g., manpage, GitBook)
```

---

## 🧠 Key Concepts

### CLI

Handles argument parsing and dispatch logic. Entry point for user interaction.

* `cli/args.py`: Parses CLI arguments
* `cli/dispatcher.py`: Handles dispatching to proper service modules
* `cli/nethawk.py`: Main entrypoint script

### Core

Houses all core runtime components, including:

* Config loading
* MongoDB interfacing
* Dynamic module loading
* Logging setup

### Services

Each protocol (HTTP, FTP, SSH, etc.) gets its own directory in `services/`. Inside:

* `__init__.py`: Declares the service class (e.g., `HTTPService`) and its `modules()`
* Module scripts (e.g., `robots.py`) must define a class with a `.run()` method.

### Libs

Common, reusable logic split by domain:

* `libs/fuzzer/`: Directory bruteforcers, virtual host discovery
* `libs/domain_resolver/`: DNS logic
* `libs/crawler/`: Passive and active crawling
* `libs/network/`: Nmap-style port scanning

---

## 🔍 Where to Contribute

### Add a New Protocol

* Create a new folder in `services/` (e.g., `ssh/`)
* Define a `SSHService` class in `__init__.py`
* Implement `modules()` to return a list of modules
* Add module(s) with a `.run()` method (your actual logic)

### Add a New HTTP Module

* Drop into `services/http/`
* Ensure the script defines a class with a `run(self, target)` method

### Add Internal Logic (e.g., a new DNS resolver)

* Contribute to `libs/domain_resolver/`

---

## 💪 Code Style & Conventions

* Follow [PEP8](https://peps.python.org/pep-0008/)
* Use `async/await` where possible
* Group I/O-related logic under `core/`
* Use `nethawk.core.logger` for all logs
* Document your modules/classes with docstrings

---

## 🔧 Setup for Local Dev

```bash
# Clone repo
$ git clone https://github.com/yourusername/nethawk.git
$ cd nethawk

# Install deps
$ poetry install

# Run CLI
$ poetry run python -m nethawk.cli.nethawk
```

---

## 📅 Testing

```bash
# Run tests
$ poetry run pytest tests/
```

* Use `tests/` for unit tests
* Prefer mocking over real network calls
* Add test coverage for new features/modules

---

## 🚪 Contributions

* PRs are welcome!
* Please open an issue first for big features
* Follow commit naming like: `feat:`, `fix:`, `refactor:`, `test:`
* Write clear, atomic commits

---

## 🌐 Community

Feel free to open issues, submit PRs, or suggest ideas. Let's push recon tooling forward.

Stay stealthy,
**NetHawk Team**
