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
        """Prepare payload with minimal pagination parameters"""
        # Start with just the essential parameters to avoid 406 errors
        payload = base_payload.copy()

        # Only add minimal pagination - try one parameter at a time
        if page == 0:
            # First request - no pagination params
            return payload
        else:
            # Subsequent requests - try simple pagination
            payload['page'] = page
            payload['limit'] = page_size
            return payload

    def _make_request(self, payload: Dict[str, Any], retries: int = 3) -> Optional[Dict[str, Any]]:
        """Make API request with retry logic"""
        for attempt in range(retries):
            try:
                logger.info(f"Attempt {attempt + 1}: Making POST request")
                logger.info(f"Payload: {json.dumps(payload, indent=2)}")

                response = self.session.post(self.base_url, json=payload, timeout=30)

                logger.info(f"Response status: {response.status_code}")
                logger.info(f"Response headers: {dict(response.headers)}")

                if response.status_code == 401:
                    logger.error("Authentication failed - token may be expired")
                    raise requests.exceptions.HTTPError("401 Unauthorized - Check your token")

                if response.status_code == 406:
                    logger.error("406 Not Acceptable - API may not support this request format")
                    logger.error(f"Response body: {response.text}")

                response.raise_for_status()

                # Log the response for debugging
                response_data = response.json()
                logger.info(f"Response data preview: {json.dumps(response_data, indent=2)[:500]}...")

                return response_data
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request attempt {attempt + 1} failed: {e}")
                if hasattr(e, 'response') and e.response is not None:
                    logger.warning(f"Response status: {e.response.status_code}")
                    if e.response.text:
                        logger.warning(f"Response body: {e.response.text[:500]}")

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

        if response is None:
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

def check_token_validity(token: str) -> bool:
    """Check if JWT token is still valid"""
    try:
        import base64
        import json
        import datetime

        # Split token and decode payload
        payload = token.split('.')[1]
        # Add padding if needed
        payload += '=' * (4 - len(payload) % 4)
        decoded = base64.b64decode(payload)
        token_data = json.loads(decoded)

        exp_time = datetime.datetime.fromtimestamp(token_data['exp'])
        current_time = datetime.datetime.now()

        logger.info(f"Token expires: {exp_time}")
        logger.info(f"Current time: {current_time}")

        return current_time < exp_time
    except Exception as e:
        logger.error(f"Error checking token validity: {e}")
        return False

def main():
    # API configuration
    url = "https://api.rready.com/PASHAHolding/users/fetchByBatch"

    # Updated with working token from browser request
    bearer_token = "eyJraWQiOiIxIiwiYWxnIjoiRWREU0EifQ.eyJpc3MiOiJraWNrYm94LWltcHJvdmUiLCJzdWIiOiJhNjE0ZWZjOC0zMmI4LTRjYjItYjgwYi1iYzRiZDAxOGVkOWQiLCJhdWQiOiJQQVNIQUhvbGRpbmciLCJjb250ZXh0cyI6WyJQQVNIQUhvbGRpbmciXSwiZXhwIjoxNzYwNjc3Mjg1fQ.GXMVeQ8gFXvzsV97V_NQ5adDW27AN-CmHFHbeIsoArKU4UoeXAc8RQnInoK_a_hjgJJ7PoJLCiae5ZGlMC6IDQ"

    # Check token validity before making requests
    if not check_token_validity(bearer_token):
        logger.error("❌ TOKEN EXPIRED! Please get a new bearer token from the API provider.")
        logger.error("   You need to authenticate again to get a fresh token.")
        print("❌ Error: Bearer token is expired!")
        print("📋 To fix this:")
        print("   1. Log into the API provider's system")
        print("   2. Generate a new bearer token")
        print("   3. Replace the 'bearer_token' variable in this script")
        return

    # Headers matching the working browser request
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "app-id": "app",
        "product": "kickbox",
        "Content-Type": "application/json",
        "Accept": "*/*",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
        "Origin": "https://app.rready.com",
        "Referer": "https://app.rready.com/"
    }

    # Base payload with correct UUID target IDs
    base_payload = {
        "targets": [
            "12017f89-4dcc-432e-9f7a-b24229bbe100","78dd388d-bd41-4a71-bc80-daf5cebf96b4","94b77a54-a4c1-4f3d-b6b3-3368a3bc661b",
            "8cb0d288-bee0-4d75-8bdd-6ac1efd14510","f782215e-f88d-475c-9bdf-57702a85a41d","fe8b834d-9724-4255-98f8-0fc9ab4a849e",
            "8bc46da5-73c8-483d-8a53-aa69663d38a1","6005f667-e557-4170-b850-76f773bf0061","df1335ca-701f-40f0-8978-c45a0a4aa539",
            "0161109d-ea97-4f51-b076-2b88d954e0b1","2f0efd72-7afb-43f1-8329-6e1e5acf012a","70e8093d-a28c-45b3-b8f3-252bd0190298",
            "99276bb1-fa4a-4170-9b29-bf9db93da5c8","f059e1ab-fc0a-4fe3-a264-765ea970d6d9","a52b6d07-1c34-4bdb-9c14-8a970378a705",
            "67571572-ca7e-426e-95ae-ceeb5c16324e","5f3d0ddc-509e-4e64-8f5b-1908ef22250b","5b69e6eb-5df7-4011-94dc-20d9e1750296",
            "8b03af1e-de8d-41e6-a2d7-3d1c4060b8f6","0f0e6974-191b-4b81-94bf-2948141c294e","2d8786bd-1c6f-457a-8c86-ef6a70667313",
            "b408a1bc-a897-40d8-87af-d1f13b738784","a614efc8-32b8-4cb2-b80b-bc4bd018ed9d","d9b8ee66-9dae-482b-b1dd-cc6646915bb9",
            "62682c37-1992-42cf-ba1c-f555b5a7e74b","28438a81-3390-4e81-b86c-ace7cb25947a","adefb661-5adf-4bb5-b91b-19cb1c480f45",
            "278bbb11-2344-47ca-9506-e170f71ec2f6","e519729f-2a37-436d-98d5-4877ce244ad7","6f40ae3f-c0d5-4d28-ac0a-7852502681eb",
            "50f653ef-41ab-4f39-b3be-df74fcb9a75e","5ae9dfac-25c4-4f6e-990c-606664e1e9ed","9bd221b6-5273-4445-bb00-3849e5824c1f",
            "b6dea228-60bc-4d00-a16a-3c488c28a75a","c3ac2254-ad36-49ff-99b6-c8cfa084cbcc","18e7365a-38b4-4eb9-b2d6-8e29af78f015",
            "ec7c572e-0c77-4218-ab40-672dfed0191d","cb0e8f92-edbd-43a1-a464-fecace5b88d0","e9232b65-ad2c-43a4-886e-43ef41c47eb8",
            "95bdbb84-b7ac-462f-bcb5-25491ac4b3eb","9304fd3c-a720-4b22-b5dd-a6be5046daef","e85ecc85-dcaa-44a0-80ec-3bd2821dee0b",
            "269ea39a-c401-4057-9ef2-f2aca7908210","34485a71-daa1-4f8d-b4c7-0f16e0dc30d0","3413153f-befa-4fb9-82dc-c1d2236c46ca",
            "3800e425-3836-49fd-a6f5-3968b5fe6826","5d2481eb-7afa-40ec-b3f9-96ac802d5839","569795dd-0835-4f97-a9e5-5f33b05ee050",
            "9d3bf335-f278-4022-bdd1-784b4d44b6e5","a3a5858a-5539-4297-b21c-4a78f45b5459","7864b4ce-08a7-49b8-9308-42036b176cb5",
            "ba5cc701-96df-455b-8005-a4d49e6e27db","426ef819-641d-4101-9aed-c258b3c5f3c2","38730372-7afa-4679-a30a-2b943459e191",
            "750fa5a5-b47e-482c-b12f-b4cc933e2f99","87dc43d1-85c7-49b7-b2ee-ddf4c0901c18","a4922393-0d1b-4569-af1c-236905d5f41c",
            "35943c68-2426-4c98-bb8a-bd86e0a6cda4","57ef6f69-b919-43e8-a534-5bd624d9e31b","b4cc05e0-e4c7-42e7-98c8-2961f88dcc72",
            "574df811-964e-4b0c-b28e-eb18d55205f8","106abdd6-60d2-45ea-94f0-557acde55f69","bcdeb57e-df61-4eca-8ecc-9e3e291e53cc",
            "72141c81-f10b-484a-8d86-0f4ba3143aba","d5b895d9-fe3a-47fd-86b0-d70be781400c","dfe54bfc-762c-4ef8-b763-66b0704fcd02",
            "b8414f15-11c4-4c99-b93e-56ddf6c7707d","55246789-175f-462d-8f10-ac43d34405cc","f3bab95a-a8b5-4f3d-aee9-66e933fbab46",
            "b6493106-aee9-49c3-b088-767c9c2aa2a6","2e8a7505-4fbc-4895-a179-24e358f5c6d8","83be7fa3-1aa8-45f1-88d1-a42c56f32320",
            "4bcb772c-c4a1-410d-9c5c-a80dad635b71","9dbd770e-e5ed-41e9-b49b-b5f7524e32c8","9d3ddd6a-1de8-4552-b35f-8b7b25182ff3",
            "de2e23ca-e27e-4d6a-a5fd-cc849ebbeef5","681710df-deab-4913-a12a-52f073237f4c","f0e6721f-c036-4d60-a414-ef59b6c51fb6",
            "6c34c1a4-d3d0-4ab2-822b-9ae5fa3ae151","971252c9-edcf-434d-811a-9f2c365f6e98","60e6400c-3568-4563-af20-23caf32bd13b",
            "2775a7d8-dc93-4824-be60-3247f09f6006","012d8356-07f8-48c4-9ec3-601358f153f2","0fe0f13f-2fd8-447e-9d28-faec2a3eb860",
            "c7efe0b3-4238-49d2-9b53-3577d7c39ec7","c90d914e-d724-443a-8772-c0b96b6143d9","31cbdbe8-e0b6-417b-8f5b-0f057c727b31",
            "7fce10fa-b6d5-44f4-a115-c9fa1da44097","5abd28e4-a26b-47e1-bdc8-d07c6db5aab2","33fe0036-f054-4a59-ac70-8fd4b366a0f0",
            "1795f13b-7ccf-4daa-9510-845285fed995","fd4a2ed6-cdc5-44b0-ac50-4ba2a6864970","94151710-6bae-4616-b9e5-7f436cf3d837",
            "58c5ce16-9270-40a2-91e9-5937ea4243a3","d3b5f268-62a7-4fc7-9cdb-c86b198dcaf1","222cb59a-1bd5-46da-ab2c-396a95a5da6a",
            "562d83b3-0d4a-4b3f-93e5-5ba0d7df6151","7aacaad9-529e-4e07-b844-90f39b1cb19d","090ca1ce-9d3a-430b-aa7c-76f25fd38748",
            "0b33d38f-75ad-4085-a06d-d439e3685207","d8b7fc77-4f28-4c35-995e-1bbcab14ab39","ee8a2e88-c13f-4378-a398-ffba5e86878c",
            "53171701-e73e-46ff-beff-c52228158e12","c266d83b-9f34-450f-9216-d0c8ec969a82","deaad702-708e-4c80-ac93-d65bb1342a1c",
            "a8fea9d3-9d93-4217-b785-38a820f7228c","156ebdb1-ddea-4e85-81ff-cc748a43494e","3dad1cbb-9b6f-42f1-bd2f-f2f88f740a13",
            "7f101b64-b027-4e90-8e81-5c744110ec8e","da243e04-3ecc-4196-89f6-b89fe42c87b1","04b61897-2d34-4f4f-bbbf-16de1d06991f",
            "68cba2f3-24ff-47ad-8a61-e86ec41f9645","48315417-3d0f-452a-9006-256b5f2ec04a","61b36321-08cc-458e-928c-5dcfd70e3794",
            "847ab46c-fb11-4779-911a-d25db6071a52","a211eb30-e1d6-4042-9c2e-40d77172208e","0f261b3f-f662-4494-a434-4e7acb52503c",
            "507aaabc-aaaa-4f21-ac9a-bdec9b67698f","e173e750-cf65-4d25-ba87-d714ef4fa819","5964b467-2cc4-4c74-9041-cdfe5d5531d6",
            "442d54d7-2a4b-45c7-a97d-e01dfb644b45","4995079b-e37f-432b-97e2-f354fd9e32b4","a0ce4e47-8a1e-4dea-9124-883df4941882",
            "ef6140b2-0321-418a-b872-f473afd821d7","e9ab45d7-1f48-44fc-9c4a-df239af7ed5a","dfdbdb89-c846-444f-ad08-adcc22d58311",
            "4e036056-9714-4933-ab43-389f6c874201","1124d0d1-96cb-41f8-bb84-570cd298f6cc","ed325578-8727-46d2-b1e3-94c9ffd4ba5a",
            "4923c266-e4d0-4706-9663-7c13682c1163","83b91567-db5b-4006-899e-8030abcf1382","99a8c81d-4d05-4eb1-9017-ecf07a6aa685",
            "9ecb9129-ebb3-431e-b9e8-15a8c679dca1","a5dbe8ba-cf0b-456c-9608-bcc6b9310086","d42e1206-2d00-408b-8e62-45d4f92be340",
            "57cef4a9-2776-4622-8a94-724796f363cc","8406ca55-6364-4934-979f-fb0225f35749","b0662995-3b5a-425d-a0cf-e92e651d4103",
            "4de5e46e-3aee-4a6a-bc3f-0f0ccc2fc6cc","046847e4-e0e0-4976-81e7-b06c398d0f34"
        ]
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