import os
import re
import requests
import sys
import time
import schedule

UNIFI_CONTROLLER_URL = os.getenv('UNIFI_CONTROLLER_URL')
UNIFI_API_TOKEN = os.getenv('UNIFI_API_TOKEN')
UNIFI_SITE = os.getenv('UNIFI_SITE', 'default')
SSL_VERIFY = os.getenv('SSL_VERIFY', 'False').lower() in ('true', '1', 't')

BLOCKLIST_URLS = os.getenv('BLOCKLIST_URLS', 'https://www.spamhaus.org/drop/drop.txt').split(',')
FIREWALL_GROUP_NAME = os.getenv('FIREWALL_GROUP_NAME', 'UniSentry Blocklist')
UPDATE_SCHEDULE_HOURS = int(os.getenv('UPDATE_SCHEDULE_HOURS', 24))

IP_REGEX = r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)(?:\/(?:3[0-2]|[12]?[0-9]))?$"

class UniFiAPI:
    def __init__(self, base_url, token, site='default', ssl_verify=False):
        self.base_url = base_url.rstrip('/')
        self.site = site

        self.headers = {
            'X-API-Key': f'{token}',
            'Content-Type': 'application/json'
        }

        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.session.verify = ssl_verify
        if not ssl_verify:
            from requests.packages.urllib3.exceptions import InsecureRequestWarning
            requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

        if not self._test_connection():
            raise Exception("Failed to authenticate with UniFi Controller. Check URL and API Token.")

    def _test_connection(self):
        print("    - Verifying API token and connection...")
        try:
            response = self.session.get(f"{self.base_url}/proxy/network/api/self/sites", timeout=10)
            response.raise_for_status()
            print("    - Token and connection verified successfully.")
            return True
        except requests.RequestException as e:
            print(f"    - Connection test failed: {e}")
            return False

    def _make_request(self, method: str, endpoint: str, data: dict = None) -> dict:
        url = f"{self.base_url}/proxy/network/api/s/{self.site}/{endpoint}"
        try:
            if method.upper() == "GET":
                response = self.session.get(url, timeout=10)
            elif method.upper() == "POST":
                response = self.session.post(url, json=data, timeout=10)
            elif method.upper() == "PUT":
                response = self.session.put(url, json=data, timeout=10)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"API request to '{url}' failed: {e}")
            if e.response is not None:
                print(f"Response body: {e.response.text}")
            raise

    def get_firewall_groups(self) -> list:
        result = self._make_request("GET", "rest/firewallgroup")
        return result.get('data', [])

    def edit_firewall_group(self, group_id: str, original_group: dict, new_members: list):
        payload = original_group.copy()
        payload['group_members'] = new_members
        self._make_request("PUT", f"rest/firewallgroup/{group_id}", data=payload)


    def create_firewall_group(self, members: list):
        payload = {'name': FIREWALL_GROUP_NAME, 'group_type': 'address-group', 'members': members}
        self._make_request("POST", "rest/firewallgroup", data=payload)


def fetch_blocklist_ips(urls):
    print(">>> Fetching IP addresses from sources...")
    ip_set = set()
    for url in urls:
        url = url.strip()
        if not url: continue
        try:
            print(f"    - Downloading from {url}")
            response = requests.get(url, timeout=20)
            response.raise_for_status()
            lines = response.text.splitlines()
            count = 0
            for line in lines:
                if line.strip().startswith('#') or not line.strip(): continue
                match = line.split(';')[0].strip()
                if re.match(IP_REGEX, match):
                    ip_set.add(match)
                    count += 1
            print(f"    - Found {count} valid IPs in list.")
        except requests.RequestException as e:
            print(f"    - [ERROR] Could not download from {url}: {e}", file=sys.stderr)
    total_ips = len(ip_set)
    print(f">>> Fetched a total of {total_ips} unique IP addresses.\n")
    return list(ip_set)

def run_update():
    print("--- UniSentry: Starting Update Run ---")

    new_ips = fetch_blocklist_ips(BLOCKLIST_URLS)
    if not new_ips:
        print("[ERROR] No IP addresses were fetched. Aborting update.", file=sys.stderr)
        return

    try:
        print(f">>> Connecting to UniFi Controller at {UNIFI_CONTROLLER_URL}...")
        controller = UniFiAPI(UNIFI_CONTROLLER_URL, UNIFI_API_TOKEN, UNIFI_SITE, SSL_VERIFY)

        print(f">>> Checking for Firewall Group '{FIREWALL_GROUP_NAME}'...")
        all_groups = controller.get_firewall_groups()
        target_group = next((g for g in all_groups if g.get('name') == FIREWALL_GROUP_NAME), None)

        new_ips.sort()

        if target_group:
            group_id = target_group['_id']
            existing_ips = sorted(target_group.get('members', []))
            print(f"    - Found existing group with ID: {group_id} ({len(existing_ips)} members).")

            if existing_ips == new_ips:
                print("\n>>> No changes detected. Firewall group is already up-to-date.")
            else:
                print(f"\n>>> Updating group with {len(new_ips)} new IPs...")
                controller.edit_firewall_group(group_id, target_group, new_ips)
                print("    - Firewall group updated successfully.")
        else:
            print(f"    - No existing group found. Creating new group with {len(new_ips)} members...")
            controller.create_firewall_group(new_ips)
            print(f"    - Successfully created new group '{FIREWALL_GROUP_NAME}'.")

    except Exception as e:
        print(f"\n[FATAL] An error occurred: {e}", file=sys.stderr)

    print("\n--- UniSentry: Update Run Finished ---\n")

def main():
    if not all([UNIFI_CONTROLLER_URL, UNIFI_API_TOKEN]):
        print("[FATAL] UNIFI_CONTROLLER_URL and UNIFI_API_TOKEN environment variables must be set.", file=sys.stderr)
        sys.exit(1)

    run_update()

    print(f">>> Scheduling update to run every {UPDATE_SCHEDULE_HOURS} hours.")
    schedule.every(UPDATE_SCHEDULE_HOURS).hours.do(run_update)

    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    main()