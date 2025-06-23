# NetHawk

![nethawk](https://img.shields.io/badge/status-active-success?style=flat-square)
![license](https://img.shields.io/github/license/yourorg/nethawk?style=flat-square)

## 🔍 Overview

**NetHawk** was built to automate and streamline **service-aware enumeration** in offensive security workflows. **Designed, Tuned and tested with 100+ OSCP-style labs**, it automates service-aware enumeration by detecting active services on a target and **executing dedicated reconnaissance tasks specific to each service protocol**, letting you **focus on strategic attack planning based on meaningful results**

* 🔗 Detects open ports & maps them to recon modules:
  *   HTTP → Technology detection, CVE Analyst, Robots Analyst, Crawler, Fuzz, etc..
  *   SMB → enum, user extraction, shares enum, file dumping, etc..
* 🧠 Service-aware logic built for automation
* 📄 Profile-based workflows (YAML) for repeatable, scripted recon
* ⚡ Async event loop engine with MongoDB-based persistence
* 🧩 Drop-in module system for rapid extension

---

## 📦 Features

* **Protocol Detection**: Auto-detects services and dispatches specialized recon modules
* **Workflow Profiles**: YAML-defined task flows enable repeatable, customizable scans
* **Modular Design**: Modules are isolated and easy to write/plug in
* **Persistence Layer**: MongoDB backend for target metadata, state, and results
* **Asynchronous Execution**: Built with concurrency in mind for fast, distributed scans

---

## 🧠 Why NetHawk?
NetHawk frees pentesters and red teamers from fragmented, manual recon by automating service-aware enumeration workflows. It acts as a smart assistant that lets you focus on strategic attack planning based on meaningful, persistent scan data — all while scaling with async concurrency and extensible plugins.

### 🔎 1. Recon is Still Too Manual and Fragmented
Most pentesters or red teamers still juggle:

* 🔧 Bash scripts
* 🔗 External recon tools (nmap, ffuf, nikto, etc.)
* 🧠 Manual note-taking
* ❌ Little chaining between tools

NetHawk aims to be the glue:

> A modular, extensible, and async-first recon framework that automates targeted service enumeration — like how you'd do it manually in an OSCP-style lab, but smarter and reproducible.

### ⚙️ 2. Auto-Driven, Service-Aware Enumeration
Instead of blindly brute-forcing or running the same scans everywhere, NetHawk:

* 📡 Uses port scan results to identify services
* 🧠 Maps services → modules automatically
* 🧪 Runs specific, protocol-aware tests (e.g., crawl /robots.txt if HTTP, check shares if SMB)

###  🧬 3. Profile-Driven, Repeatable Workflows
* YAML-defined profiles allow repeatable scans
* You can define:
  * Which modules to run
  * In what order
  * With what params
> No more “I forgot to run that one enum script” problems.

---

## 🤝 Contributing

We welcome PRs! Read:

* [CONTRIBUTING.md](./CONTRIBUTING.md) for code guidelines
* [DEVELOPER.md](./DEVELOPER.md) for architectural insights

---

## ⚖️ License

MIT — See [LICENSE](./LICENSE)
