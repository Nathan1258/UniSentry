import os, sys, re
import requests
import schedule, time
from pyunifi.controller import Controller

UNIFI_CONTROLLER_URL = os.getenv('UNIFI_CONTROLLER_URL')
UNIFI_USERNAME = os.getenv('UNIFI_USERNAME')
UNIFI_PASSWORD = os.getenv('UNIFI_PASSWORD')
UNIFI_SITE = os.getenv('UNIFI_SITE', 'default')
UNIFI_PORT = os.getenv('UNIFI_PORT', '8443')
# Important: For UDM/UXG, set this to False if using a local IP without a valid SSL certificate
SSL_VERIFY = os.getenv('SSL_VERIFY', 'True').lower() in ('true', '1', 't')

BLOCKLIST_URLS = os.getenv('BLOCKLIST_URLS', 'https://www.spamhaus.org/drop/drop.txt').split(',')
FIREWALL_GROUP_NAME = os.getenv('FIREWALL_GROUP_NAME', 'Dynamic Blocklist')
UPDATE_SCHEDULE_HOURS = int(os.getenv('UPDATE_SCHEDULE_HOURS', 24))

IP_REGEX = r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)(?:\/(?:3[0-2]|[12]?[0-9]))?$"

def fetch_blocklist_ips(urls):
    """Fetches IP addresses from a list of URLs and returns a unique set."""
    print(">>> Fetching IP addresses from sources...")
    ip_set = set()
    for url in urls:
        if not url:
            continue
        try:
            print(f"    - Downloading from {url}")
            response = requests.get(url, timeout=20)
            response.raise_for_status()

            lines = response.text.splitlines()
            count = 0
            for line in lines:
                if line.strip().startswith('#') or not line.strip():
                    continue
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
    """Connects to UniFi and updates the firewall group."""
    print("--- UniSentry: Starting Update Run ---")

    new_ips = fetch_blocklist_ips(BLOCKLIST_URLS)
    if not new_ips:
        print("[ERROR] No IP addresses were fetched. Aborting update to avoid emptying the list.", file=sys.stderr)
        return

    try:
        print(f">>> Connecting to UniFi Controller at {UNIFI_CONTROLLER_URL}...")
        controller = Controller(
            UNIFI_CONTROLLER_URL,
            UNIFI_USERNAME,
            UNIFI_PASSWORD,
            site_id=UNIFI_SITE,
            ssl_verify=SSL_VERIFY,
            version='UDM'
        )
        print("    - Connection successful.\n")

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
                controller.edit_firewall_group(group_id, FIREWALL_GROUP_NAME, new_ips)
                print("    - Firewall group updated successfully.")
        else:
            print(f"    - No existing group found. Creating new group with {len(new_ips)} members...")
            controller.create_firewall_group(FIREWALL_GROUP_NAME, 'address-group', new_ips)
            print(f"    - Successfully created new group '{FIREWALL_GROUP_NAME}'.")

    except Exception as e:
        print(f"\n[FATAL] An error occurred during the update run: {e}", file=sys.stderr)

    print("\n--- UniSentry: Update Run Finished ---\n")

def main():
    if not UNIFI_CONTROLLER_URL:
        print("[FATAL] UNIFI_CONTROLLER_URL environment variable must be set", file=sys.stderr)

    if not all([UNIFI_CONTROLLER_URL, UNIFI_USERNAME, UNIFI_PASSWORD]):
        print("[FATAL] UNIFI_CONTROLLER_URL, UNIFI_USERNAME, and UNIFI_PASSWORD environment variables must be set.", file=sys.stderr)
        sys.exit(1)

    run_update()

    print(f">>> Scheduling update to run every {UPDATE_SCHEDULE_HOURS} hours.")
    schedule.every(UPDATE_SCHEDULE_HOURS).hours.do(run_update)

    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    main()