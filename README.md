# 💰 Net Worth Tracker 💹

🌟 _Effortlessly monitor your portfolio balance in one place!_ 🌟

`net-worth-tracker` allows you to keep track of your stock, cash, and crypto portfolio, making it easy to see your total net worth without the need to check multiple platforms. 📈🔍

Supported data sources for stock/cash financial data include:

*   Mint 💵
*   Brand New Day 🌅
*   DeGiro 📊

Supported data sources for crypto portfolio data include:

*   Nexo.io 💎
*   Binance Smart Chain (BEP20 tokens + DeFi via🌐)
*   Binance.com 🪙
*   Exodus wallet 💼
*   ApeBoard for tracking on many DeFi chains 🦍
*   CoinGecko (for prices) 🦎
*   Beefy vaults 🐄
*   Yearn V3 🔄


## Download Relase
🚀 Install --> [Releases]()


## 🚀 Getting Started

### Usage

Run [`crypto-tracker.ipynb`](crypto-tracker.ipynb) and download the appropriate data.

Set up a cronjob, using `crontab -e`:

```javascript
0 * * * * ~/Sync/Overig/crypto-tracker/run-and-upload.sh
```

### Installation 🛠️

To install required packages and tools, follow these steps:

1.  Install Python dependencies:

```
pip install -r requirements.txt
```

2.  Install `chromedriver`:

```bash
sudo apt install chromium-chromedriver keychain # Ubuntu
brew cask install chromedriver  # MacOS
```

## 📚 Documentation

_Coming soon!_

## 🤝 Contributing

We welcome contributions! Feel free to submit issues or pull requests to improve the project. 🙌

## 📃 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
