# 🌌 Skyblock flipper

A specialized Python terminal designed to identify profit margins between raw Bazaar materials and their crafted counterparts. By pulling real-time data from the Hypixel API and cross-referencing it with the NotEnoughUpdates (NEU) item database, this tool automates the math behind Bazaar flipping.

---

## 🚀 Features
* **Bazaar-Centric Data**: Optimized for speed by ignoring the Auction House and focusing solely on high-volume Bazaar items.
* **Automated Recipe Fetching**: Uses the NEU item repository to automatically determine ingredients for any valid Bazaar item ID.
* **Live ROI Analytics**: 
    * **Craft Cost**: Calculated via "Insta-Buy" (Sell Summary) prices.
    * **Unit Profit**: Calculated via "Insta-Sell" (Buy Summary) prices minus the 1.25% Bazaar tax.
* **Visual Trend Analysis**: Integrated Matplotlib chart shows price action for your target item over the current session.
* **Purse Sync**: Link your profile to see exactly how many items you can craft with your current in-game balance.

---

## 🛠️ Installation

### 1. Requirements
* **Python 3.10+**
* **Hypixel API Key** (Generate one at [developer.hypixel.net](https://developer.hypixel.net/))

### 2. Setup Libraries
Open your terminal and run:
```bash
pip install requests matplotlib python-dotenv