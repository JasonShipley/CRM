# Hetzner VPS Provisioning Checklist (5–10 minutes)

This creates the production server for MCE's Twenty CRM. Total cost: ~€5–9/month.

## 1. Create the account
1. Go to https://accounts.hetzner.com/signUp and sign up with an MCE email
   (e.g. jason@usemce.com). Use company billing details.
2. New accounts may be asked for ID verification — normal, usually minutes.

## 2. Create the server
1. Go to https://console.hetzner.cloud → **New project** → name it `MCE CRM`.
2. **Add server** with:
   - **Location:** Ashburn, VA (US East) if offered for the type below — otherwise
     Falkenstein or Helsinki (EU) is fine (the app is fast either way; EU saves money).
   - **Image:** Ubuntu 24.04
   - **Type:** Shared vCPU x86 — pick the ~4 GB RAM option (e.g. CX23/CPX21 class,
     2 vCPU / 4 GB / 40+ GB disk). ~€4–9/mo depending on location.
   - **Networking:** IPv4 + IPv6 (defaults)
   - **SSH key:** paste the public key I give you, or skip and Hetzner emails a root
     password (either works — I'll set up keys on first login).
   - **Backups:** enable (20% surcharge ≈ €1–2/mo) — recommended; this is the
     server-level safety net on top of the CRM's own nightly database backups.
   - **Name:** `mce-crm`
3. Click **Create & Buy now**.

## 3. DNS (you said MCE has domains)
Pick the domain you want (e.g. `crm.usemce.com`) and add an **A record** pointing to
the server's IPv4 address (shown in the Hetzner console after creation).
TLS certificates are issued automatically once DNS resolves (Let's Encrypt, free).

## 4. Hand me access
Send me:
- The server IP
- Root access: either tell me the SSH key you installed is mine, or share the root
  password Hetzner emailed (I'll immediately switch the server to key-only login)
- The DNS name you chose

I take it from there: install Docker, deploy the same stack validated in the build
environment, restore the migrated data, set up nightly backups and auto-restart, and
hand you the login URL.
