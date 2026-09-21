.PHONY: setup run test app clean

setup:
	python -m venv .venv
	. .venv/bin/activate; pip install -r requirements.txt

run:
	python -m vireo.pipeline

test:
	pytest -q

app:
	streamlit run app/app.py

clean:
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +
	rm -rf .pytest_cache
