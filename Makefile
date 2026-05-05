.PHONY: setup run test lint help

# The default action when you just type 'make'
help:
	@echo "💰 Personal Finance Manager"
	@echo ""
	@echo "Available commands:"
	@echo "  make setup  - 📦 First-time setup (creates venv + installs everything)"
	@echo "  make run    - 🚀 Start the app in your browser"
	@echo "  make test   - 🧪 Run all automated tests"
	@echo "  make lint   - 🧹 Check code style"

setup:
	@echo "📦 Setting up your environment..."
	python3 -m venv venv
	. venv/bin/activate && pip install -r requirements.txt
	@echo ""
	@echo "✅ All done! Run 'make run' to start the app."

run:
	@echo "🚀 Starting Personal Finance Manager..."
	. venv/bin/activate && streamlit run app.py

test:
	@echo "🧪 Running tests..."
	. venv/bin/activate && python -m pytest tests/ -v

lint:
	@echo "🧹 Checking code style..."
	. venv/bin/activate && python -m flake8 --max-line-length=120 app.py database.py views/
