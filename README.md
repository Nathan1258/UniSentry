# 🛡️ UniSentry: UniFi Blocklist Updater

A simple, self-scheduling, containerized tool to automatically update a UniFi Network firewall group with IP addresses from one or more blocklist URLs.

This container runs continuously, updating your blocklist immediately on startup and then again on a recurring schedule.

**🐳 Docker Hub Image:** `nathan12581/unisentry`

---

## 🚀 Setup & Configuration

Follow these two parts to get UniSentry up and running.

### Part 1: UniFi Controller Setup

First, we need to prepare your UniFi Network Application by creating the necessary firewall rules.

#### Prerequisites
1.  **Docker:** Must be installed on a 24/7 server or NAS that can reach your UniFi Controller.
2.  **UniFi OS Console:** A UDM, UDM Pro, UDM-SE, UXG-Pro, etc.
3.  **Local Admin Account:** You **must** use a Local Account for the UniFi OS Console, not a Ubiquiti SSO Cloud Account.
    * Go to your UniFi Console > **Settings > Admins & Users > Create New Admin**.
    * Check **Restrict to Local Access Only**.
    * Enter Username and password. **unisentry** as the username is recommended for the sake of consistency
    * Uncheck **Use a Predefiend Role** to allow customisation.
    * Assign it a "Full Management" role to **Network** and "None" to user management.

#### Create Firewall Policies
Navigate to **Settings > Policy Engine** in your UniFi Controller and create the following two firewall rules.

**1️⃣ Block Inbound Threats**
This rule prevents malicious IPs from reaching your network.

- **Name:** `UniSentry - Block Inbound Threats`
- **Action:** `Block`
- **Source Zone:** `External`
- **Destination Zone:** `Any`
- **Source Object:** Under the **Source** section:
    1.  Select **Object**.
    2.  Click **Create New Object**.
    3.  **Type:** `IPv4 Address Group`
    4.  **Name:** `UniSentry Blocklist`  *(⚠️ This name **must match** your `FIREWALL_GROUP_NAME` environment variable.)*
    5.  **Address:** Add a single placeholder IP like `192.0.2.1` (the script will overwrite this).
    6.  Click **Add** to save the object.
- Finally, click **Add Policy** to save the rule.

**2️⃣ Block Outbound Threats**
This rule prevents internal devices from communicating with malicious IPs.

- **Name**: `UniSentry - Block Outbound Threats`
- **Action**: `Block`
- **Source Zone**: `Internal`
- **Destination Zone**: `External`
- **Destination Object**: Under the **Destination** section:
    1. Select **Object**.
    2. Choose the `UniSentry Blocklist` group you created in the previous rule.
- Finally, click **Add Policy** to save the rule.

### Part 2: Running UniSentry

Now, deploy the UniSentry container.

#### Using Docker Compose (Recommended)
1.  Create a file named `docker-compose.yml` on your Docker host.
2.  Paste the following content, editing the `environment` section with your details.

    ```yaml
    version: '3.8'

    services:
      unifisentry:
        image: nathan12581/unisentry:latest
        container_name: unisentry
        restart: unless-stopped
        environment:
          # --- UniFi Controller Configuration (CHANGE THESE) ---
          - UNIFI_CONTROLLER_URL=[https://192.168.1.1](https://192.168.1.1)
          - UNIFI_USERNAME=your_local_admin
          - UNIFI_PASSWORD=your_secret_password
          - SSL_VERIFY=False

          # --- UniSentry Configuration (Optional) ---
          - FIREWALL_GROUP_NAME="UniSentry Blocklist"
          - UPDATE_SCHEDULE_HOURS=24
          - BLOCKLIST_URLS="[https://www.spamhaus.org/drop/drop.txt,https://rules.emergingthreats.net/fwrules/emerging-Block-IPs.txt](https://www.spamhaus.org/drop/drop.txt,https://rules.emergingthreats.net/fwrules/emerging-Block-IPs.txt)"
          - TZ=Europe/London
    ```
3.  Start the container:
    ```bash
    docker-compose up -d
    ```
    You can view logs with `docker-compose logs -f`.

#### Using Docker Run
If you prefer not to use Docker Compose, run this single command after filling in your details:
```bash
docker run -d \
  --name unisentry \
  --restart unless-stopped \
  -e UNIFI_CONTROLLER_URL="[https://192.168.1.1](https://192.168.1.1)" \
  -e UNIFI_USERNAME="your_local_admin" \
  -e UNIFI_PASSWORD="your_secret_password" \
  -e SSL_VERIFY="False" \
  -e FIREWALL_GROUP_NAME="UniSentry Blocklist" \
  -e UPDATE_SCHEDULE_HOURS="24" \
  -e BLOCKLIST_URLS="[https://www.spamhaus.org/drop/drop.txt,https://rules.emergingthreats.net/fwrules/emerging-Block-IPs.txt](https://www.spamhaus.org/drop/drop.txt,https://rules.emergingthreats.net/fwrules/emerging-Block-IPs.txt)" \
  -e TZ="Europe/London" \
  nathan12581/unisentry:latest
  ```

  ---

## ⚙️ Environment Variables

| Variable                | Default                               | Description                                                                                             |
| ----------------------- | ------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| `UNIFI_CONTROLLER_URL`  | (None)                                | **Required.** Full URL to your UniFi Controller.                                                        |
| `UNIFI_USERNAME`        | (None)                                | **Required.** The username for a local admin account.                                                     |
| `UNIFI_PASSWORD`        | (None)                                | **Required.** The password for the local admin account.                                                   |
| `SSL_VERIFY`            | `False`                               | Set to `True` if your controller uses a valid, trusted SSL certificate.                                   |
| `FIREWALL_GROUP_NAME`   | `UniSentry Blocklist`                 | The name of the firewall group to create/update. Must match the name used in your firewall rules.       |
| `UPDATE_SCHEDULE_HOURS` | `24`                                  | The interval, in hours, between update checks.                                                          |
| `BLOCKLIST_URLS`        | (Defaults to Spamhaus)                | A comma-separated list of URLs pointing to text files containing IP addresses.                          |
| `TZ`                    | (None)                                | Optional, but recommended. Set your timezone (e.g., `America/New_York`) for correct log timestamps. |
| `UNIFI_SITE`            | `default`                             | The UniFi site to modify. `default` is correct for most setups.                                         |

---

## 🤝 Contributing

Contributions are welcome! If you have a suggestion for a new feature, find a bug, or want to improve the code, please feel free to:

-   **Open an issue:** Describe the bug or feature request in detail.
-   **Submit a pull request:** Fork the repository, make your changes, and submit a pull request for review.

---

## 🙏 Acknowledgements

-   This project relies on the **[Py-unifi](https://github.com/ubiquiti-community/py-unifi/)** library to communicate with the UniFi Controller API.
-   Threat intelligence data is sourced from reputable providers like **Spamhaus**, **Emerging Threats**, and **abuse.ch**. Please respect their terms of service.