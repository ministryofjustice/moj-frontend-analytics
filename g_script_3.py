import requests
from datetime import date
import time

# GitHub API settings
SEARCH_URL = "https://api.github.com/search/code"
CREATE_ISSUE_BASE_URL = "https://api.github.com/repos"
TOKEN = "your_personal_access_token" #addd token
HEADERS = {
  "Authorization": f"token {TOKEN}",
  "Accept": "application/vnd.github+json"
}
KEYWORDS = [
  "class=\"moj-datepicker",
  "class=\"moj-pagination",
  "class=\"moj-page-header-actions"
]

# Retry settings
MAX_RETRIES = 5
WAIT_TIME = 3600


def make_request_with_retries(url, method="GET", headers=None, params=None, data=None):
  retries = 0
  while retries < MAX_RETRIES:
    if method == "GET":
      response = requests.get(url, headers=headers, params=params)
    elif method == "POST":
      response = requests.post(url, headers=headers, json=data)
    else:
      raise ValueError("Unsupported HTTP method.")

    if response.status_code == 200 or response.status_code == 201:
      return response  # Successful response
    elif response.status_code == 403:
      print(f"403 Forbidden - Retry {retries + 1}/{MAX_RETRIES}")
      time.sleep(WAIT_TIME)
      retries += 1
    else:
      print(f"Error: {response.status_code} - {response.json().get('message', 'Unknown error')}")
      break

  # If we exhaust retries, return the final response or None
  print("Max retries reached or non-recoverable error occurred.")
  return None


def search_github_code_global(keyword, per_page=100):
  all_results = []
  page = 1

  while True:
    params = {
      "q": keyword,
      "per_page": per_page,
      "page": page
    }

    response = make_request_with_retries(SEARCH_URL, method="GET", headers=HEADERS, params=params)

    if response and response.status_code == 200:
      items = response.json().get("items", [])
      all_results.extend(items)

      # Stop if there are no more results
      if len(items) < per_page:
        break

      page += 1
    else:
      break

  return all_results


def create_github_issue(title, body=None, labels=None):
  owner = "ministryofjustice"
  repo = "moj-frontend-analytics"
  data = {
    "title": title,
    "body": body,
    "labels": labels or []
  }

  url = f"{CREATE_ISSUE_BASE_URL}/{owner}/{repo}/issues"

  response = make_request_with_retries(url, method="POST", headers=HEADERS, data=data)

  if response and response.status_code == 201:
    print(f"Issue created successfully: {response.json()['html_url']}")
    return response.json()
  else:
    print("Failed to create issue.")
    return None


# Run the script
def start():
  for keyword in KEYWORDS:
    results = search_github_code_global(keyword)

    if results:
      print(f"Found {len(results)} results for keyword: {keyword}\n")
      body = f"Issue created on: {date.today()}"

      for i, result in enumerate(results, start=1):
        create_github_issue(result['repository']['full_name'], body, [keyword])
    else:
      print(f"No results found for keyword: {keyword}")


if __name__ == "__main__":
  start()
