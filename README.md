# BTC Order Book Aggregator
A Python script that aggregates BTC-USD order book data from two exchanges, it parses and normalizes them into two lists: bids & asks, bids sorted by descending price, asks sorted by ascending price, and calculates the total cost and revenue for buying or selling a specified amount of BTC.

## Setup Instructions
1. **Clone the repository:**
   git clone https://github.com/xxAndres1606/btc_orderbook_aggregator.git
   cd btc_orderbook_aggregator

2. **Create virtual environment:**
   python -m venv venv_name
   source venv_name/bin/activate #--> macOS

3. **Install dependencies:**
   pip install requests

4. **Run the script:**
   python main.py --qty number
   The script accepts a --qty argument to specify the BTC quantity, the default quantity is 10

## Assumptions:
For analyzing the structure of the Coinbase data, I was able to determine that each entry in bids and asks is: [price, size, num_orders], by visiting the Coinbase Exchange API documentation, link: https://docs.cdp.coinbase.com/api-reference/exchange-api/rest-api/products/get-product-book

## Issues encounteded:
While pushing the script to GitHub, the HTTPS authentication failed since password-based authentication is no longer supported. I was able to resolve this by installing and authorizing the GitHub CLI via Homebrew.

brew install gh
gh auth login

