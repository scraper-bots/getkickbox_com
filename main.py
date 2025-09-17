import requests
import json
import time
import csv
import pandas as pd
from typing import Dict, List, Any, Optional
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class APIDataFetcher:
    def __init__(self, base_url: str, headers: Dict[str, str] = None):
        self.base_url = base_url
        self.headers = headers or {}
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.all_data = []

    def _prepare_pagination_payload(self, base_payload: Dict[str, Any], page: int, page_size: int) -> Dict[str, Any]:
        """Prepare payload with various pagination parameter combinations"""
        pagination_params = {
            # Common pagination patterns
            'page': page,
            'pageSize': page_size,
            'limit': page_size,
            'offset': page * page_size,
            'skip': page * page_size,
            'size': page_size,
            'pageNumber': page + 1,  # 1-based indexing
            'perPage': page_size,
            'take': page_size,
        }

        # Create a copy of base payload and add pagination params
        payload = base_payload.copy()
        payload.update(pagination_params)
        return payload

    def _make_request(self, payload: Dict[str, Any], retries: int = 3) -> Optional[Dict[str, Any]]:
        """Make API request with retry logic"""
        for attempt in range(retries):
            try:
                response = self.session.post(self.base_url, json=payload, timeout=30)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request attempt {attempt + 1} failed: {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error(f"All {retries} attempts failed")
                    raise
        return None

    def _extract_data_from_response(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract data array from response, handling various response structures"""
        # If response is already an array
        if isinstance(response, list):
            return response

        # Common data field names
        data_fields = ['data', 'results', 'items', 'users', 'records', 'content']

        for field in data_fields:
            if field in response and isinstance(response[field], list):
                return response[field]

        # If no recognized data field, return the response as is
        logger.warning("Could not find data array in response, returning full response")
        return [response] if isinstance(response, dict) else []

    def _detect_pagination_info(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Detect pagination information from response"""
        pagination_info = {
            'has_pagination': False,
            'total_pages': None,
            'total_records': None,
            'current_page': None,
            'page_size': None,
            'has_more': False
        }

        if isinstance(response, list):
            # Direct array response - no pagination
            return pagination_info

        # Look for pagination indicators
        pagination_fields = {
            'total_pages': ['totalPages', 'total_pages', 'pageCount', 'pages'],
            'total_records': ['totalRecords', 'total', 'totalCount', 'count', 'totalElements'],
            'current_page': ['currentPage', 'page', 'pageNumber'],
            'page_size': ['pageSize', 'limit', 'size', 'perPage'],
            'has_more': ['hasMore', 'has_more', 'hasNext', 'has_next']
        }

        for key, possible_fields in pagination_fields.items():
            for field in possible_fields:
                if field in response:
                    pagination_info[key] = response[field]
                    pagination_info['has_pagination'] = True

        return pagination_info

    def fetch_all_data(self, base_payload: Dict[str, Any], page_size: int = 100, max_pages: int = 1000) -> List[Dict[str, Any]]:
        """Fetch all data with automatic pagination detection"""
        self.all_data = []
        page = 0

        logger.info("Starting data fetch...")

        # First request to detect pagination
        first_payload = self._prepare_pagination_payload(base_payload, page, page_size)
        response = self._make_request(first_payload)

        if not response:
            logger.error("Failed to get initial response")
            return []

        # Extract data and pagination info
        data = self._extract_data_from_response(response)
        pagination_info = self._detect_pagination_info(response)

        self.all_data.extend(data)
        logger.info(f"Page {page + 1}: Retrieved {len(data)} records")

        # If no pagination detected or no more data
        if not pagination_info['has_pagination'] or len(data) < page_size:
            logger.info(f"No pagination detected or end of data reached. Total records: {len(self.all_data)}")
            return self.all_data

        # Continue fetching if pagination is detected
        logger.info(f"Pagination detected. Total pages: {pagination_info.get('total_pages', 'unknown')}")

        while page < max_pages:
            page += 1

            # Rate limiting
            time.sleep(0.5)

            payload = self._prepare_pagination_payload(base_payload, page, page_size)
            response = self._make_request(payload)

            if not response:
                logger.warning(f"Failed to get response for page {page + 1}")
                break

            data = self._extract_data_from_response(response)

            if not data or len(data) == 0:
                logger.info(f"No more data on page {page + 1}. Stopping.")
                break

            self.all_data.extend(data)
            logger.info(f"Page {page + 1}: Retrieved {len(data)} records. Total so far: {len(self.all_data)}")

            # Check if we've reached the end
            if len(data) < page_size:
                logger.info("Received less data than page size. Likely reached end.")
                break

            # Check pagination info for stopping condition
            pagination_info = self._detect_pagination_info(response)
            if pagination_info.get('has_more') is False:
                logger.info("API indicates no more data available.")
                break

            if pagination_info.get('total_pages') and page >= pagination_info['total_pages']:
                logger.info(f"Reached total pages limit: {pagination_info['total_pages']}")
                break

        logger.info(f"Data fetch completed. Total records retrieved: {len(self.all_data)}")
        return self.all_data

    def save_to_file(self, filename: str = "api_data.json"):
        """Save all fetched data to a JSON file"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.all_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Data saved to {filename}")
        except Exception as e:
            logger.error(f"Failed to save data to file: {e}")

    def save_to_csv(self, filename: str = "api_data.csv"):
        """Save all fetched data to a CSV file"""
        try:
            if not self.all_data:
                logger.warning("No data to save")
                return

            # Get all unique keys from all records
            all_keys = set()
            for record in self.all_data:
                if isinstance(record, dict):
                    all_keys.update(record.keys())

            # Convert to list and sort for consistent column order
            fieldnames = sorted(list(all_keys))

            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                for record in self.all_data:
                    if isinstance(record, dict):
                        # Handle nested objects by converting to JSON strings
                        row = {}
                        for key in fieldnames:
                            value = record.get(key, '')
                            if isinstance(value, (dict, list)):
                                row[key] = json.dumps(value, ensure_ascii=False)
                            else:
                                row[key] = value
                        writer.writerow(row)

            logger.info(f"Data saved to {filename}")
        except Exception as e:
            logger.error(f"Failed to save data to CSV file: {e}")

    def save_to_xlsx(self, filename: str = "api_data.xlsx"):
        """Save all fetched data to an Excel file"""
        try:
            if not self.all_data:
                logger.warning("No data to save")
                return

            # Convert data to DataFrame
            df_data = []
            for record in self.all_data:
                if isinstance(record, dict):
                    # Flatten nested objects
                    flattened = {}
                    for key, value in record.items():
                        if isinstance(value, (dict, list)):
                            flattened[key] = json.dumps(value, ensure_ascii=False)
                        else:
                            flattened[key] = value
                    df_data.append(flattened)

            df = pd.DataFrame(df_data)

            # Save to Excel
            df.to_excel(filename, index=False, engine='openpyxl')
            logger.info(f"Data saved to {filename}")
        except Exception as e:
            logger.error(f"Failed to save data to Excel file: {e}")

    def save_all_formats(self, base_filename: str = "api_data"):
        """Save data in all formats (JSON, CSV, XLSX)"""
        self.save_to_file(f"{base_filename}.json")
        self.save_to_csv(f"{base_filename}.csv")
        self.save_to_xlsx(f"{base_filename}.xlsx")

def main():
    # API configuration
    url = "https://api.rready.com/PASHAHolding/users/fetchByBatch"

    headers = {
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2NjlhMzQ2ODU5ZjM5OTAwMTJhZTJjZjUiLCJpYXQiOjE3MjY1NjUzNjEsImV4cCI6MTcyNzE3MDE2MX0.dZKYPQ1yVDpAOBKd8llJO-m7fxuKW_xdvVR7kG1AXzY",
        "app-id": "669a1b2159f3990012ae2c73",
        "product": "pashabank",
        "Content-Type": "application/json"
    }

    # Base payload (modify as needed)
    base_payload = {
        "targets": ["6693bae9e7f59e001266b25b", "669a346859f3990012ae2cf5"]
    }

    # Create fetcher instance
    fetcher = APIDataFetcher(url, headers)

    # Fetch all data
    try:
        all_data = fetcher.fetch_all_data(base_payload, page_size=100)

        # Save to all formats
        fetcher.save_all_formats("fetched_data")

        print(f"Successfully fetched {len(all_data)} records")
        print(f"Data saved to:")
        print(f"  - fetched_data.json")
        print(f"  - fetched_data.csv")
        print(f"  - fetched_data.xlsx")

    except Exception as e:
        logger.error(f"Error during data fetch: {e}")
        print(f"Error: {e}")

if __name__ == "__main__":
    main()