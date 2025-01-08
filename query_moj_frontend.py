import json
import logging
import os
import time
from datetime import date

import requests

# GitHub API settings
SEARCH_URL = "https://api.github.com/search/code"
CREATE_ISSUE_BASE_URL = "https://api.github.com/repos"
TOKEN = os.environ.get('GH_TOKEN')
HEADERS = {
  "Authorization": f"token {TOKEN}",
  "Accept": "application/vnd.github+json"
}
EXTENSIONS = ["njk", "js", "html", "erb", "php", "vue", "gotmpl", "cshtml"]
COMPONENTS = {
    "moj-datepicker": {
        "class_query": 'class="moj-datepicker',
        "nunjucks_query": 'import mojDatePicker extension:njk' 
    },
    "moj-pagination": {
        "class_query": 'class="moj-pagination',
        "nunjucks_query": 'import mojPagination extension:njk' 
    }
}

# Retry settings
MAX_RETRIES = 10  # code search limits to 1000 results
WAIT_TIME = 60  # code search api rate limit is 10 requests / min

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def make_request_with_retries(url, method="GET", headers=None, params=None, data=None):
    logger.info(f"making request to url: {url} with params: {params}")
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
            logger.info(f"403 Forbidden - Retry {retries + 1}/{MAX_RETRIES}")
            time.sleep(WAIT_TIME)
            retries += 1
        else:
            logger.info(f"Error: {response.status_code} - {response.json().get('message', 'Unknown error')}")
            break

    # If we exhaust retries, return the final response or None
    print("Max retries reached or non-recoverable error occurred.")
    return None


def search_github(query, results=None, per_page=100):
    results = results or {
        "count": 0,
        "items": []
    }

    page = 1

    while True:
        params = {
            "q": f'{query}',
            "per_page": per_page,
            "page": page,
            "sort": "indexed",  # sort by date indexed
            "order": "desc"  # sort descending to ensure we get newest results in the search
        }
        response = make_request_with_retries(SEARCH_URL, method="GET", headers=HEADERS, params=params)

        if response and response.status_code == 200:
            logger.info(f"total results: {response.json()['total_count']}")
            results['count'] = results['count'] + response.json()['total_count']
            items = response.json().get("items", [])
            logger.info(f"items count: {len(items)}")
            logger.info(f"cumulative items count: {results['count'] + response.json()['total_count']}")
            for item in items:
                results["items"].append({
                        "repository": item['repository']['full_name'],
                        "owner": item['repository']['owner']['login'],
                        "url": item['repository']['html_url'],
                        "path": item['path'],
                        "extension": item['path'].split('.')[-1],
                        "description": item['repository']['description'],
                        "date": date.today().strftime('%d/%m/%y %H:%M:%S')
                    })

            # Stop if there are no more results
            if len(items) < per_page:
                logger.info(f"{query} results done")
                break

            page += 1
        else:
            break

    return results


def process_queries(queries):
    results = {
        "count": 0,
        "items": []
    }

    for query_type, query in queries.items():
        total_results = None
        if query_type == "class_query":
            #make intitial query and check count
            params = {
                "q": f'{query}',
            }
            logger.info(f"processing {query_type}: {query}")
            response = make_request_with_retries(SEARCH_URL, method="GET", headers=HEADERS, params=params)

            if response and response.status_code == 200:
                print(f"total results: {response.json()['total_count']}")
                total_results = response.json()['total_count']

            if total_results and total_results < 1000:
                results = search_github(query, results)
            else:
                logger.info("too many results filtering by extension")
                for extension in EXTENSIONS:
                    ext_query = f'{query} extension:{extension}'
                    logger.info(f"processing {query_type}: {ext_query}")
                    results = search_github(ext_query, results)

        else:
            logger.info(f"processing {query_type}: {query}")
            results = search_github(query, results)

    return results


def save_json_to_repo(data, filename):
    try:
        # Ensure filename has .json extension
        if not filename.endswith('.json'):
            filename += '.json'

        logger.info(f"Saving JSON to {filename}")

        # Save the file
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        logger.info("File saved successfully")
        return True

    except Exception as e:
        logger.error(f"Error saving file: {str(e)}")
        return False


# Run the script
if __name__ == "__main__":
    all_results = {}
    for component, queries in COMPONENTS.items():
        results = process_queries(queries)

        if results:
            print(f"Found {len(results["items"])} results for component: {component}\n")
            all_results[component] = results
        else:
            print(f"No results found for component: {component}")

    # save json file
    success = save_json_to_repo(all_results, 'results.json')
    exit(0 if success else 1)
