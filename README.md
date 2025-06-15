# 🛡️ UniSentry: UniFi Blocklist Updater

A simple, self-scheduling, containerized tool to automatically update a UniFi Network firewall group with IP addresses from one or more blocklist URLs. This version uses modern, secure API Token authentication.

This container runs continuously, updating your blocklist immediately on startup and then again on a recurring schedule.

**🐳 Docker Hub Image:** `nathan12581/unisentry`

---

## 🚀 Setup & Configuration

Follow these two parts to get UniSentry up and running.

### Part 1: UniFi Controller Setup

First, we'll create the necessary API Token and Firewall Policies in your UniFi Network Application.

#### Prerequisites
1.  **Docker:** Must be installed on a 24/7 server or NAS that can reach your UniFi Controller.
2.  **UniFi OS Console:** A UDM, UDM Pro, UDM-SE, UXG-Pro, etc.

#### 1. Create an API Key 🔑
UniSentry authenticates using a dedicated API Token.

1.  Log in to your UniFi Console as the owner or a Super Admin.
2.  Go to **Control Panel > Integrations**.
3.  Click **Create API Key**.
4.  Give it a descriptive name (e.g., `UniSentry Token`).
5.  Set the **Token Expiration** to **Never**.
6  Click **Add**.
7  **Important:** Copy the generated token immediately and save it somewhere safe. You will not be able to see it again. This is your `UNIFI_API_TOKEN`.

#### 2. Create Firewall Policies 🚦
Navigate to **Settings > Policy Engine > Firewall** and create the following two firewall rules.

**Rule 1: Block Inbound Threats**
-   **Name:** `UniSentry - Block Inbound Threats`
-   **Action:** `Block`
-   **Source Zone:** `External`
-   **Destination Zone:** `Any`
-   **Source Object:** Under the **Source** section:
    1.  Select **Object** and click **Create New Object**.
    2.  **Type:** `IPv4 Address Group`
    3.  **Name:** `UniSentry Blocklist`  *(⚠️ This name **must match** your `FIREWALL_GROUP_NAME` environment variable.)*
    4.  **Address:** Add a single placeholder IP like `192.0.2.1` (the script will overwrite this).
    5.  Click **Add** to save the object.
-   Click **Add Policy** to save the rule.

**Rule 2: Block Outbound Threats**
-   **Name**: `UniSentry - Block Outbound Threats`
-   **Action**: `Block`
-   **Source Zone**: `Internal`
-   **Destination Zone**: `External`
-   **Destination Object**: Under the **Destination** section, select **Object** and choose the `UniSentry Blocklist` group.
-   Click **Add Policy** to save the rule.

### Part 2: Running UniSentry

Deploy the container using Docker Compose.

1.  Create a file named `docker-compose.yml` on your Docker host.
2.  Paste the following content, editing the `environment` section with your details.

    ```yaml
    services:
      unifisentry:
        image: nathan12581/unisentry:latest
        container_name: unisentry
        restart: unless-stopped
        environment:
          # --- UniFi Controller Configuration (REQUIRED) ---
          - UNIFI_CONTROLLER_URL=[https://192.168.1.1](https://192.168.1.1)
          - UNIFI_API_TOKEN=your_secret_api_token_here

          # --- Optional Configuration ---
          - SSL_VERIFY=False # Set to True if your controller has a valid SSL certificate
          - FIREWALL_GROUP_NAME=UniSentry Blocklist
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
  -e UNIFI_API_TOKEN="your_secret_api_token_here" \
  -e SSL_VERIFY="False" \
  -e FIREWALL_GROUP_NAME="UniSentry Blocklist" \
  -e UPDATE_SCHEDULE_HOURS="24" \
  -e BLOCKLIST_URLS="[https://www.spamhaus.org/drop/drop.txt,https://rules.emergingthreats.net/fwrules/emerging-Block-IPs.txt](https://www.spamhaus.org/drop/drop.txt,https://rules.emergingthreats.net/fwrules/emerging-Block-IPs.txt)" \
  -e TZ="Europe/London" \
  nathan12581/unisentry:latest

---

## ⚙️ Environment Variables

| Variable                | Default                               | Description                                                                                             |
| ----------------------- | ------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| `UNIFI_CONTROLLER_URL`  | (None)                                | **Required.** Full base URL to your UniFi Controller (e.g., `https://192.168.1.1`).                      |
| `UNIFI_API_TOKEN`       | (None)                                | **Required.** The API token you generated in the UniFi settings.                                          |
| `SSL_VERIFY`            | `False`                               | Set to `True` if your controller uses a valid, trusted SSL certificate.                                   |
| `FIREWALL_GROUP_NAME`   | `UniSentry Blocklist`                 | The name of the firewall group to create/update. Must match the name used in your firewall rules.       |
| `UPDATE_SCHEDULE_HOURS` | `24`                                  | The interval, in hours, between update checks.                                                          |
| `BLOCKLIST_URLS`        | (Defaults to Spamhaus)                | A comma-separated list of URLs pointing to text files containing IP addresses.                          |
| `UNIFI_SITE`            | `default`                             | The UniFi site to modify. `default` is correct for most setups.                                         |
| `TZ`                    | (None)                                | Optional, but recommended. Set your timezone (e.g., `America/New_York`) for correct log timestamps. |

---

## 🤝 Contributing

Contributions are welcome! If you have a suggestion for a new feature, find a bug, or want to improve the code, please feel free to:

-   **Open an issue:** Describe the bug or feature request in detail.
-   **Submit a pull request:** Fork the repository, make your changes, and submit a pull request for review.

---

## 🙏 Acknowledgements

-   This project uses the official UniFi Network Application API.
-   Threat intelligence data is sourced from reputable providers like **Spamhaus** and **Emerging Threats**. Please respect their terms of service.