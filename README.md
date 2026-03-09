
# First time (headed, may require interactive login or EMAIL/PASSWORD in .env)
uv run python -m scripts.run_reports --fresh-login

# Run all reports using saved auth (headed)
uv run python -m scripts.run_report

# Run specific reports (headed)
uv run python -m scripts.run_reports --reports r10_mill_table_audit r11_lumber_chip_summary

# Headless (e.g., on CI) with saved auth
uv run python -m scripts.run_reports --headless

