import os
import re
import requests
import sys
import asyncio
import unifi_client
from unifi_client.rest import ApiException

UNIFI_CONTROLLER_URL = os.getenv('UNIFI_CONTROLLER_URL')
UNIFI_USERNAME = os.getenv('UNIFI_USERNAME')
UNIFI_PASSWORD = os.getenv('UNIFI_PASSWORD')
SSL_VERIFY = os.getenv('SSL_VERIFY', 'True').lower() in ('true', '1', 't')

BLOCKLIST_URLS = os.getenv('BLOCKLIST_URLS', 'https://www.spamhaus.org/drop/drop.txt').split(',')
FIREWALL_GROUP_NAME = os.getenv('FIREWALL_GROUP_NAME', 'UniSentry Blocklist')
UPDATE_SCHEDULE_HOURS = int(os.getenv('UPDATE_SCHEDULE_HOURS', 24))

IP_REGEX = r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)(?:\/(?:3[0-2]|[12]?[0-9]))?$"

def fetch_blocklist_ips(urls):
    print(">>> Fetching IP addresses from sources...")
    ip_set = set()
    for url in urls:
        url = url.strip()
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

async def run_update():
    print("--- UniSentry: Starting Update Run ---")

    new_ips = fetch_blocklist_ips(BLOCKLIST_URLS)
    if not new_ips:
        print("[ERROR] No IP addresses were fetched. Aborting update.", file=sys.stderr)
        return

    configuration = unifi_client.Configuration(
        host = UNIFI_CONTROLLER_URL,
        username = UNIFI_USERNAME,
        password = UNIFI_PASSWORD
    )

    try:
        async with unifi_client.ApiClient(configuration) as api_client:
            api_instance = unifi_client.FirewallGroupApi(api_client)

            print(f">>> Checking for Firewall Group '{FIREWALL_GROUP_NAME}'...")
            api_response = await api_instance.list_firewall_group()

            target_group = next((g for g in api_response.data if g.name == FIREWALL_GROUP_NAME), None)

            new_ips.sort()

            if target_group:
                group_id = target_group.id
                existing_ips = sorted(target_group.members)
                print(f"    - Found existing group with ID: {group_id} ({len(existing_ips)} members).")

                if existing_ips == new_ips:
                    print("\n>>> No changes detected. Firewall group is already up-to-date.")
                else:
                    print(f"\n>>> Updating group with {len(new_ips)} new IPs...")
                    update_request = unifi_client.FirewallGroupUpdateRequest(
                        name=FIREWALL_GROUP_NAME,
                        group_type='address-group',
                        members=new_ips
                    )
                    await api_instance.update_firewall_group(group_id, firewall_group_update_request=update_request)
                    print("    - Firewall group updated successfully.")
            else:
                print(f"    - No existing group found. Creating new group with {len(new_ips)} members...")
                new_group = unifi_client.FirewallGroup(
                    name=FIREWALL_GROUP_NAME,
                    group_type='address-group',
                    members=new_ips
                )
                await api_instance.create_firewall_group(firewall_group=new_group)
                print(f"    - Successfully created new group '{FIREWALL_GROUP_NAME}'.")

    except ApiException as e:
        print(f"\n[FATAL] An API error occurred: {e}", file=sys.stderr)
    except Exception as e:
        print(f"\n[FATAL] A general error occurred: {e}", file=sys.stderr)

    print("\n--- UniSentry: Update Run Finished ---\n")

async def main():
    if not all([UNIFI_CONTROLLER_URL, UNIFI_USERNAME, UNIFI_PASSWORD]):
        print("[FATAL] UNIFI_CONTROLLER_URL, UNIFI_USERNAME, and UNIFI_PASSWORD must be set.", file=sys.stderr)
        sys.exit(1)

    await run_update()

    print(f">>> Scheduling update to run every {UPDATE_SCHEDULE_HOURS} hours.")
    while True:
        await asyncio.sleep(UPDATE_SCHEDULE_HOURS * 3600)
        await run_update()

if __name__ == "__main__":
    asyncio.run(main())