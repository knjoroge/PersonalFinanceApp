.PHONY: setup run test lint requirements help

# The default action when you just type 'make'
help:
	@echo "💰 Personal Finance Manager"
	@echo ""
	@echo "Available commands:"
	@echo "  make setup  - 📦 First-time setup (installs everything with uv)"
	@echo "  make run    - 🚀 Start the app in your browser"
	@echo "  make test   - 🧪 Run all automated tests"
	@echo "  make lint   - 🧹 Check code style"

setup:
	@echo "📦 Setting up your environment..."
	uv sync
	@echo ""
	@echo "✅ All done! Run 'make run' to start the app."

run:
	@echo "🚀 Starting Personal Finance Manager..."
	uv run streamlit run app.py

test:
	@echo "🧪 Running tests..."
	uv run pytest tests/ -v

lint:
	@echo "🧹 Checking code style..."
	uv run flake8 --max-line-length=120 app.py database.py views/

# Regenerate requirements.txt (used by run.command / run.bat) after changing pyproject.toml
requirements:
	uv lock
	uv export --no-hashes --no-dev --no-emit-project -o requirements.txt
