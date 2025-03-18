# sowclassic-compendium

Welcome to the SoW Classic compendium!

🚀 **An automated bot that scrapes the weekly leaderboard from [Secrets of War Classic](https://sowclassic.com) and posts it as a GitHub Discussion.**  
It is fully automated using **GitHub Actions** and **GitHub App authentication**.

📖 **Looking for game guides and documentation?**  
Check out the **[SoW Classic Handbook](./handbook/)** for rules, strategies, and more.

---

## **📌 Features**
- **Scrapes the Top Players** weekly using Selenium.
- **Tracks Rank & Power Changes** by comparing against the previous week.
- **Converts relative timestamps** (e.g., "20 days ago") to absolute dates.  
- **Posts to [GitHub Discussions](https://github.com/maegju/sowclassic-compendium/discussions).**
- **Stores leaderboard history in JSON** (`leaderboard_log.json`) for accurate comparisons.
- **Ensures correct week tracking**
- **Runs automatically every Monday at 12:00 UTC via GitHub Actions.**  
- **Can also be triggered manually via GitHub Actions UI.**  

---

## **📅 Automated Schedule**
The bot is **fully automated** using **GitHub Actions** and runs:
- **🕛 Every Monday at 12:00 UTC**
- **🔁 Can be manually triggered anytime via GitHub Actions.**

---

## **⚡ How to Manually Run the Bot**
1. **Go to the [GitHub Actions Page](https://github.com/maegju/sowclassic-compendium/actions).**
2. Click on **"Weekly Leaderboard Bot"**.
3. Click **"Run Workflow"** to trigger it instantly.

---

## **🛠️ How It Works**
1. **The bot scrapes `sowclassic.com/toplists`** using **Selenium**.
2. **Extracts leaderboard data** (Rank, Name, Power, Created).
3. **Formats the data** into a **Markdown table**.
4. **Posts the leaderboard** in [GitHub Discussions](https://github.com/maegju/sowclassic-compendium/discussions).
5. **Runs automatically every Monday** or can be run manually.
