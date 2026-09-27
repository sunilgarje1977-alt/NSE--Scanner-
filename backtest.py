  backtest5000:
    if: github.event_name == 'workflow_dispatch'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with: {python-version: '3.9'}
      - run: pip install yfinance pandas requests
      - run: python Backtest_5000.py
        env:
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
      - uses: actions/upload-artifact@v3
        with:
          name: backtest-5000-csv
          path: backtest_5000_60days.csv
