# UniSentry: UniFi Blocklist Updater

A simple, self-scheduling, containerised tool to automatically update a UniFi Network firewall group with IP addresses from one or more blocklist URLs.

This container runs continuously, updating your blocklist immediately on startup and then again on a recurring schedule (defaulting to every 24 hours).

**Docker Hub Image:** `nathan12581/unifisentry`

## Prerequisites

1.  **Docker:** Must be installed on a 24/7 server or NAS that can reach your UniFi Controller.
2.  **UniFi OS Console:** A UDM, UDM Pro, UDM-SE, UXG-Pro, etc.
3.  **Local Admin Account:** You **must** use a Local Account for the UniFi OS Console, not a Ubiquiti SSO Cloud Account.
    * Go to your UniFi Console > Settings > Admins > Add New Admin.
    * Set **Account Type** to **Local Access**.
    * Assign it a "Limited Admin" role with **Administrator** access to the Network application.

## 1. UniFi Controller Setup

Before running UniSentry, you must create firewall rules that use the group the script will manage.

1.  Navigate to **UniFi Network > Settings > Security > Firewall**.
2.  Under **Rules > WAN IN**, create a new rule:
    * **Action:** `Drop`
    * **Source > IPv4 Address Group:** Select "Create New Group".
        * **Name:** `UniSentry Blocklist` (This name must match the `FIREWALL_GROUP_NAME` variable).
        * Leave members empty.
    * **Rule is applied:** Before predefined rules.
3.  Create another rule under **WAN OUT**:
    * **Action:** `Drop`
    * **Destination > IPv4 Address Group:** Select the `UniSentry Blocklist` group.
    * **Rule is applied:** Before predefined rules.

## 2. Running UniSentry

### Using Docker Compose (Recommended)

1.  Create a file named `docker-compose.yml` on your Docker host.
2.  Copy and paste the following content into the file, editing the `environment` section with your details.

    ```yaml
    version: '3.8'

    services:
      unifisentry:
        image: nathan12581/unifisentry:latest
        container_name: unifisentry
        restart: unless-stopped
        environment:
          # --- UniFi Controller Configuration (CHANGE THESE) ---
          - UNIFI_CONTROLLER_URL=http://192.168.1.1
          - UNIFI_USERNAME=your_local_admin_username
          - UNIFI_PASSWORD=your_local_admin_password
          - SSL_VERIFY=False

          # --- UniSentry Configuration (Optional: Customise these) ---
          - FIREWALL_GROUP_NAME=UniSentry Blocklist
          - UPDATE_SCHEDULE_HOURS=24 # How often to check for updates, in hours.
          - BLOCKLIST_URLS="https://www.spamhaus.org/drop/drop.txt,https://rules.emergingthreats.net/fwrules/emerging-Block-IPs.txt,https://feodotracker.abuse.ch/downloads/ipblocklist.txt"
          - TZ=Europe/London # Set your timezone
    ```

3.  Start the container in detached mode:

    ```bash
    docker-compose up -d
    ```

    UniSentry will now run in the background, updating your list automatically. You can view its logs with `docker-compose logs -f`.

### Using Docker Run

If you prefer not to use Docker Compose, you can use a single `docker run` command.

```bash
docker run -d \
  --name unisentry \
  --restart unless-stopped \
  -e UNIFI_CONTROLLER_URL="https://192.168.1.1" \
  -e UNIFI_USERNAME="your_local_admin" \
  -e UNIFI_PASSWORD="your_secret_password" \
  -e SSL_VERIFY="False" \
  -e FIREWALL_GROUP_NAME="UniSentry Blocklist" \
  -e UPDATE_SCHEDULE_HOURS="24" \
  -e BLOCKLIST_URLS="https://www.spamhaus.org/drop/drop.txt,https://rules.emergingthreats.net/fwrules/emerging-Block-IPs.txt" \
  -e TZ="Europe/London" \
  nathan12581/unifisentry:latest