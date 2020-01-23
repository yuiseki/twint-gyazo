default:
	@echo "usage: make <command>"
	@echo "commands:"
	@echo "  bundle"

bundle:
	pip install twint
	pip install requests
	pip install beautifulsoup4