import os
import time
import json
import requests
import re
import jwt
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# GitHub Config
GITHUB_REPO = "maegju/sowclassic-compendium"
GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"
DISCUSSION_CATEGORY_ID = os.getenv("DISCUSSION_CATEGORY_ID")  # Get from GitHub API
APP_ID = os.getenv("APP_ID")  # Set this in GitHub Secrets
APP_PRIVATE_KEY = os.getenv("APP_PRIVATE_KEY")  # Store the .pem key content in Secrets
LEADERBOARD_LOG_PATH = "bot/leaderboard_log.json"

# 📥 Load Leaderboard Log (Keeps Only Last 3 Weeks)
def load_leaderboard_log():
    """Loads the leaderboard log and retains only the last 3 weeks in correct order."""
    if not os.path.exists(LEADERBOARD_LOG_PATH):
        return {}

    with open(LEADERBOARD_LOG_PATH, "r") as f:
        leaderboard_log = json.load(f)

    # Convert to a list of (week, data) pairs and keep the last 3 weeks
    leaderboard_items = list(leaderboard_log.items())[-3:]  # Keep last 3 in original order

    return dict(leaderboard_items)

# 📤 Save Leaderboard Log
def save_leaderboard_to_json(week, leaderboard):
    """Saves the first leaderboard of the week while keeping only the last 3 weeks, appending new weeks at the end."""
    leaderboard_log = load_leaderboard_log()

    # Append new week if not already recorded
    if week not in leaderboard_log:
        leaderboard_log[week] = {
            player: {"rank": int(rank), "power": int(power.replace(",", ""))}
            for rank, player, power, created in leaderboard
        }
        print(f"✅ Week {week} appended to leaderboard log.")

    # Convert to a list of tuples (week, data) to keep chronological order
    leaderboard_items = list(leaderboard_log.items())

    # Keep only the last 3 weeks, preserving order
    leaderboard_items = leaderboard_items[-3:]  

    # Convert back to dictionary to save
    leaderboard_log = dict(leaderboard_items)

    # Save to JSON file
    with open(LEADERBOARD_LOG_PATH, "w") as f:
        json.dump(leaderboard_log, f, indent=4)

    # Commit changes to GitHub so the file persists
    commit_leaderboard_log()

# 📌 Commit JSON Log to GitHub
def commit_leaderboard_log():
    """Commits and pushes leaderboard_log.json back to the GitHub repository."""
    os.system("git config --global user.name 'maegjubot[bot]'")
    os.system("git config --global user.email '203464359+maegjubot[bot]@users.noreply.github.com'")
    os.system("git add bot/leaderboard_log.json")
    os.system("git commit -m 'Update leaderboard_log.json [Automated]' || echo 'No changes to commit'")
    os.system("git push")

def scrape_leaderboard():
    """Scrapes the leaderboard using Selenium."""
    url = "https://sowclassic.com/toplists"
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(url)

    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "table")))
        leaderboard_table = driver.find_elements(By.TAG_NAME, "table")[0]  # First table
        rows = leaderboard_table.find_elements(By.TAG_NAME, "tr")[1:]  # Skip header row

        rank_mapping = {"🥇": "1", "🥈": "2", "🥉": "3"}  # Convert emojis to numbers

        leaderboard = []
        for row in rows:
            columns = row.find_elements(By.TAG_NAME, "td")
            if len(columns) >= 4:
                rank = columns[0].text.strip()
                rank = rank_mapping.get(rank, rank)  # Convert emoji rank if applicable
                player = columns[1].text.strip()
                power = columns[2].text.strip()
                created = convert_relative_to_absolute(columns[3].text.strip())

                leaderboard.append((rank, player, power, created))

        driver.quit()
        return leaderboard
    except Exception as e:
        driver.quit()
        raise Exception(f"Error scraping leaderboard: {e}")

def convert_relative_to_absolute(relative_time):
    """Converts relative time (e.g., '20 days ago') to absolute dates (YYYY-MM-DD)."""
    match = re.match(r"(\d+) (day|hour|minute|week|month|year)s? ago", relative_time)
    if not match:
        return "Unknown"

    amount, unit = int(match.group(1)), match.group(2)
    now = datetime.utcnow()

    unit_map = {
        "minute": timedelta(minutes=amount),
        "hour": timedelta(hours=amount),
        "day": timedelta(days=amount),
        "week": timedelta(weeks=amount),
        "month": timedelta(days=30 * amount),
        "year": timedelta(days=365 * amount)
    }

    return (now - unit_map.get(unit, timedelta())).strftime("%Y-%m-%d")

# 🔐 Generate GitHub JWT for Authentication
def generate_github_jwt():
    """Generates a JWT for GitHub App authentication."""
    now = int(time.time())
    payload = {
        "iat": now,
        "exp": now + (10 * 60),  # 10-minute expiry
        "iss": APP_ID
    }

    private_key = APP_PRIVATE_KEY.replace("\\n", "\n")  # Ensure proper newline formatting
    return jwt.encode(payload, private_key, algorithm="RS256")

# 🔑 Get GitHub Installation Token
def get_installation_token():
    """Fetches the installation access token for the GitHub App."""
    jwt_token = generate_github_jwt()

    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    # Get the installation ID
    response = requests.get(f"https://api.github.com/app/installations", headers=headers)
    installation_id = response.json()[0]["id"]

    # Generate an access token for the installation
    token_response = requests.post(
        f"https://api.github.com/app/installations/{installation_id}/access_tokens",
        headers=headers
    )

    return token_response.json()["token"]


# 🔄 Compute Rank & Power Changes
def compute_leaderboard_changes(new_leaderboard, old_leaderboard):
    """Compares new and old leaderboards to compute rank and power changes."""
    updated_leaderboard = []

    for rank, player, power, created in new_leaderboard:
        prev_data = old_leaderboard.get(player, {})
        prev_rank = prev_data.get("rank", None)
        prev_power = prev_data.get("power", None)

        # Handle unlisted players
        if prev_rank is None:
            rank_change = "Unlisted"
            power_change = "N/A"
        else:
            rank_diff = prev_rank - int(rank)
            rank_change = f"+{rank_diff}" if rank_diff > 0 else f"{rank_diff}" if rank_diff < 0 else "-"

            power_diff = int(power.replace(",", "")) - prev_power
            power_change = f"+{power_diff:,}" if power_diff > 0 else f"{power_diff:,}" if power_diff < 0 else "-"

        updated_leaderboard.append((rank, player, power, rank_change, power_change, created))

    return updated_leaderboard

# 📌 Create GitHub Discussion
def create_github_discussion(leaderboard):
    """Posts the leaderboard as a GitHub Discussion using the GitHub App."""
    GITHUB_TOKEN = get_installation_token()  # Get the app authentication token

    # Get current date details
    current_date = datetime.utcnow()
    current_week = int(current_date.strftime("%V"))  # ISO week number
    current_year = int(current_date.strftime("%Y"))  # Year

    # Compute the previous week (handling year transitions)
    if current_week == 1:  # If it's the first week of the year
        previous_year = current_year - 1
        previous_week = 52  # Assume 52 (some years have W53, but this works for most cases)
    else:
        previous_year = current_year
        previous_week = current_week - 1

    previous_week_key = f"{previous_year}-W{previous_week:02d}"  # Format as "YYYY-WXX"
    current_week_key = f"{current_year}-W{current_week:02d}"  # Format as "YYYY-WXX"

    leaderboard_log = load_leaderboard_log()
    old_leaderboard = leaderboard_log.get(previous_week_key, {})  # Compare against previous week

    print(f"🔍 Comparing against previous week: {previous_week_key}")
    updated_leaderboard = compute_leaderboard_changes(leaderboard, old_leaderboard)

    # Save the new leaderboard for the current week
    save_leaderboard_to_json(current_week_key, leaderboard)

    # 📝 Preface and Explanation Section
    preface = f"""
### 🏆 Weekly Leaderboard - Week {current_week} ({current_year})
**Weekly leaderboard created from [sowclassic.com/toplists](https://sowclassic.com/toplists).**  
This leaderboard tracks player rankings and power changes from the first recorded instance of the previous week.

---
"""

    # 📝 Create Markdown Table
    table_header = "| 🏆 | Name | Power | Rank Change | Power Change | Member Since |\n|----|------|--------|-------------|-------------|-------------|\n"
    table_rows = "\n".join([f"| {rank} | {player} | {power} | {rank_change} | {power_change} | {created} |" for rank, player, power, rank_change, power_change, created in updated_leaderboard])
    discussion_body = f"{preface}\n{table_header}{table_rows}"

    query = """
    mutation($repoId: ID!, $categoryId: ID!, $title: String!, $body: String!) {
        createDiscussion(input: {repositoryId: $repoId, categoryId: $categoryId, title: $title, body: $body}) {
            discussion {
                url
            }
        }
    }
    """

    variables = {
        "repoId": get_repository_id(),
        "categoryId": DISCUSSION_CATEGORY_ID,
        "title": f"🏆 Weekly Top Players - Week {current_week} ({current_year})",
        "body": discussion_body
    }

    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    response = requests.post(GITHUB_GRAPHQL_URL, json={"query": query, "variables": variables}, headers=headers)
    response_data = response.json()

    if response.status_code == 200 and response_data.get("data"):
        discussion_url = response_data["data"]["createDiscussion"]["discussion"]["url"]
        print(f"✅ Discussion created successfully! View it here: {discussion_url}")
    else:
        raise Exception(f"❌ Failed to create discussion: {response_data}")

def get_repository_id():
    """Fetches the correct repository ID using GitHub GraphQL API."""
    query = """
    query($repoName: String!, $owner: String!) {
        repository(name: $repoName, owner: $owner) {
            id
        }
    }
    """

    owner, repo = GITHUB_REPO.split("/")
    headers = {"Authorization": f"token {get_installation_token()}", "Accept": "application/vnd.github.v3+json"}
    response = requests.post(GITHUB_GRAPHQL_URL, json={"query": query, "variables": {"repoName": repo, "owner": owner}}, headers=headers)

    if response.status_code == 200 and response.json().get("data", {}).get("repository"):
        return response.json()["data"]["repository"]["id"]
    else:
        raise Exception(f"❌ Failed to fetch repository ID: {response.json()}")

def main():
    leaderboard = scrape_leaderboard()
    if leaderboard:
        create_github_discussion(leaderboard)

if __name__ == "__main__":
    main()