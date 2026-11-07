eval:
	.venv/bin/python -m evals.run

eval-fast:
	.venv/bin/python -m evals.run --skip-gemini

test:
	.venv/bin/python -m pytest -q tests
