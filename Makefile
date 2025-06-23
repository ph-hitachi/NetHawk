# Define variables
VENV_NAME = .venv
PYTHON = python3
PIP = pip

# Install the project in editable mode
install:
	@echo "Checking virtual environment..."
	@if [ ! -d "$(VENV_NAME)" ]; then \
		echo "Creating virtual environment..."; \
		$(PYTHON) -m venv $(VENV_NAME); \
	fi
	@echo "Installing project in editable mode..."
	. $(VENV_NAME)/bin/activate && pip install -e .
	
reinstall:
	@echo "Reinstalling the package..."
	. $(VENV_NAME)/bin/activate && pip uninstall -y nethawk && pip install -e .

install-man:
	install -d $(DESTDIR)/usr/share/man/man1
	install -m 644 docs/man/nethawk.1 $(DESTDIR)/usr/share/man/man1/nethawk.1
	gzip -f $(DESTDIR)/usr/share/man/man1/nethawk.1
	
# Run the project
run:
	@echo "Running the project..."
	. $(VENV_NAME)/bin/activate && nethawk

# Run tests using pytest
test:
	@echo "Running tests with pytest..."
	. $(VENV_NAME)/bin/activate && pytest

# Clean the environment (delete virtual environment)
clean:
	@echo "Cleaning up virtual environment..."
	rm -rf $(VENV_NAME)

# Format the code using ruff (if installed)
format:
	@echo "Formatting the code..."
	. $(VENV_NAME)/bin/activate && ruff .

# Lint the code using ruff (if installed)
lint:
	@echo "Linting the code..."
	. $(VENV_NAME)/bin/activate && ruff check .

# Type check the code using mypy (if installed)
typecheck:
	@echo "Running type checks..."
	. $(VENV_NAME)/bin/activate && mypy nethawk

# Reset the environment and reinstall
reset: clean install

