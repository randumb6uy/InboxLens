# Google Cloud Project & Gmail API OAuth2 Setup Guide

This guide walks you through setting up a Google Cloud project, enabling the Gmail API with the **read-only** scope (`https://www.googleapis.com/auth/gmail.readonly`), and generating the `credentials.json` file needed by **IndexLens**.

---

## Step 1: Create a Google Cloud Project

1. Navigate to the [Google Cloud Console](https://console.cloud.google.com/).
2. Log in with the Google / Gmail account whose inbox you want to analyze.
3. Click the **Project Selector** dropdown at the top-left of the header bar.
4. Click **New Project** in the modal.
5. Enter a **Project Name** (e.g., `IndexLens`) and click **Create**.
6. Ensure your newly created project is selected in the top bar.

---

## Step 2: Enable the Gmail API

1. In the left navigation menu (or search bar), go to **APIs & Services** > **Enabled APIs & Services**.
2. Click **+ ENABLE APIS AND SERVICES** at the top.
3. Search for `Gmail API`.
4. Click on **Gmail API** in the results, then click the **Enable** button.

---

## Step 3: Configure the OAuth Consent Screen

Before generating client credentials, Google requires you to configure the OAuth consent screen.

1. In the left menu, select **APIs & Services** > **OAuth consent screen**.
2. Under **User Type**, select **External** (unless you are using a Google Workspace organization account, in which case you can select **Internal**).
3. Click **Create**.
4. Fill in the required **App Information**:
   - **App name**: `IndexLens`
   - **User support email**: Select your email address.
   - **Developer contact information**: Enter your email address.
5. Click **Save and Continue**.

### Setting Scopes
6. On the **Scopes** page, click **Add or Remove Scopes**.
7. In the search filter box, type `gmail.readonly`.
8. Locate and check the box for:
   - `.../auth/gmail.readonly` — *View your email messages and settings*
9. Click **Update** at the bottom, then click **Save and Continue**.

### Adding Test Users (Critical for "External" mode)
10. While your app is in "Testing" publishing status, only registered test users can authenticate.
11. On the **Test users** page, click **+ ADD USERS**.
12. Enter your Gmail address (the one you plan to log in with).
13. Click **Add**, then click **Save and Continue**.
14. Review the summary and click **Back to Dashboard**.

---

## Step 4: Create OAuth2 Desktop Client Credentials

1. In the left navigation menu, go to **APIs & Services** > **Credentials**.
2. Click **+ CREATE CREDENTIALS** at the top, then choose **OAuth client ID**.
3. Under **Application type**, select **Desktop app**.
4. Set the **Name** to `IndexLens Desktop Client` (or any friendly name).
5. Click **Create**.
6. A dialog titled **OAuth client created** will appear:
   - Click **DOWNLOAD JSON**.
7. Rename the downloaded file to exactly:
   ```text
   credentials.json
   ```
8. Move `credentials.json` into the root folder of this project:
   ```text
   C:\Users\tushar\Documents\codes\IndexLens\credentials.json
   ```

> [!IMPORTANT]
> `credentials.json` contains sensitive client secrets. It is already included in `.gitignore` and must **never** be committed to Git.

---

## Step 5: Test & Authenticate

Once `credentials.json` is in place, run the live fetch command in your terminal:

```powershell
.venv\Scripts\python -m src.cli fetch --live --limit 10
```

### What to Expect on First Run:
1. A browser window will automatically open asking you to sign in with your Google account.
2. Select your Google account (must match the **Test User** added in Step 3).
3. You may see a warning screen: *"Google hasn't verified this app"*.
   - This is normal for unverified private development apps.
   - Click **Advanced** (bottom left), then click **Go to IndexLens (unsafe)**.
4. On the permissions screen, review the read-only permission request (*"View your email messages and settings"*) and click **Continue**.
5. Once complete, you will see a browser message: *"The authentication flow has completed. You may close this window."*
6. A `token.json` file will automatically be generated in your project root. Subsequent commands will reuse `token.json` without opening your browser again.

---

## Troubleshooting & FAQ

### Error: `403: access_denied` / `User has not completed the verification process`
- **Cause**: You selected "External" mode on the OAuth consent screen, but forgot to add your Gmail address to the **Test Users** list.
- **Fix**: Go to **APIs & Services** > **OAuth consent screen** > **Test users** and add your Gmail address.

### Token Expiration
- While an app is in "Testing" mode, OAuth refresh tokens expire after **7 days**.
- If your token expires, simply delete `token.json` and run the CLI command again to re-authenticate.

### Switching Back to Synthetic/Mock Mode
- If you ever want to run without hitting live Gmail APIs, run with `--mock` or set `MOCK_GMAIL=true` in your `.env` file:
  ```powershell
  .venv\Scripts\python -m src.cli ingest --mock --limit 100
  ```
