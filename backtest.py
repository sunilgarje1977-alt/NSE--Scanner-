 name: NSE Backtest
on:
  workflow_dispatch:
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - name: Install deps
        run: pip install smartapi-python pandas requests pyotp
      - name: Run Backtest
        env:
          ANGEL_API_KEY: ${{ secrets.ANGEL_API_KEY }}
          ANGEL_CLIENT_ID: ${{ secrets.ANGEL_CLIENT_ID }}
          ANGEL_PASSWORD: ${{ secrets.ANGEL_PASSWORD }}
          ANGEL_TOTP_SECRET: ${{ secrets.ANGEL_TOTP_SECRET }}
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
        run: python backtest.py
