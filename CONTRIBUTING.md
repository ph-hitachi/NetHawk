# 🤝 Contributing to NetHawk

We welcome contributions to NetHawk! Whether you're fixing bugs, adding new features, or improving documentation, your help is appreciated.

Before you start, please take a moment to read through this guide.

## How to Contribute

1.  **Open an Issue:** For significant changes or new features, please open an issue first to discuss your ideas. This helps avoid duplicate work and ensures your contribution aligns with the project's goals.
2.  **Fork the Repository:** Fork the NetHawk repository on GitHub.
3.  **Clone Your Fork:** Clone your forked repository to your local machine.
4.  **Create a Branch:** Create a new branch for your contribution.
5.  **Make Your Changes:** Implement your changes, following the code style guidelines below.
6.  **Test Your Changes:** Ensure your changes work as expected and don't introduce new issues.
7.  **Commit Your Changes:** Write clear, atomic commits. Follow the commit naming conventions:
    -   `feat:` for new features
    -   `fix:` for bug fixes
    -   `refactor:` for code refactoring
    -   `test:` for adding or improving tests
    -   `docs:` for documentation changes
8.  **Push to Your Fork:** Push your branch to your fork on GitHub.
9.  **Open a Pull Request:** Open a pull request from your branch to the main NetHawk repository. Provide a clear description of your changes.

## Code Style and Guidelines

*   Follow the existing code style within the project.
*   Ensure your code is well-commented where necessary.
*   Write tests for new features or bug fixes.
*   Prefer using early returns to avoid deep nesting.
*   Prioritize code readability and performance.

## Project Structure Overview

NetHawk has a modular architecture. For a detailed overview of the project structure, please refer to the [DEVELOPER.md](./DEVELOPER.md) file.

Key directories include:

*   `nethawk/cli/`: CLI entrypoints and user interface
*   `nethawk/core/`: Core runtime, async logic, config, execution
*   `nethawk/data/`: Config files and profile definitions
*   `nethawk/libs/`: Internal libraries used by services
*   `nethawk/services/`: Protocol-specific service modules
*   `tests/`: Unit and integration tests
*   `docs/`: Documentation

## Adding New Features

If you're looking to add new functionality, here are some common areas:

*   **Add a New Protocol:** Create a new folder in `services/` and define a service class. See [DEVELOPER.md](./DEVELOPER.md) for details.
*   **Add a New HTTP Module:** Drop your script into `services/http/` and ensure it has a `run(self, target)` method. See [DEVELOPER.md](./DEVELOPER.md) for details.
*   **Add Internal Logic:** Contribute to the relevant directory within `libs/` (e.g., `libs/domain_resolver/`). See [DEVELOPER.md](./DEVELOPER.md) for details.

Thank you for contributing to NetHawk!