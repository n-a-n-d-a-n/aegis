# Aegis — Operational Security Guide

This document is for journalists and operators running Aegis.
Technical security is only one layer. OpSec failures are usually human.

---

## For Journalists (Receiving End)

### Private Key Handling

- Generate your keypair on an **air-gapped machine** (one that has never been
  and will never be connected to the internet)
- Store `journalist_private.pem` on an **encrypted USB drive** (VeraCrypt or
  native OS encryption)
- Never copy the private key to a cloud drive, email, or any networked storage
- The USB drive should be stored physically securely — locked drawer, safe, etc.
- Consider having a second encrypted copy stored in a separate physical location

### Decrypting Submissions

- Always decrypt on a machine that is **offline** at the time of decryption
- Preferably use a dedicated machine (even a cheap laptop) that is only used
  for this purpose
- After decryption, if you need to move the content, transfer via encrypted
  USB — not email or cloud
- Wipe decrypted files securely after use (`shred -u filename` on Linux)

### Accessing the Admin Panel

- Use the mTLS client certificate issued via Cloudflare Access
- Enable FIDO2 hardware key (YubiKey or similar) as your second factor
- Never access the admin panel from a public or untrusted network
- Consider using a VPN or Tor when accessing the admin panel

---

## For Submitters (Sending End)

Aegis's README should include the following guidance for submitters.
The platform protects the network layer — the device layer is the submitter's responsibility.

### Highest Safety (Recommended for Sensitive Submissions)

1. Obtain a USB drive and download [Tails OS](https://tails.boum.org/)
2. Boot from the Tails USB on any computer (leaves no trace on the host machine)
3. Use Tails' built-in Tor Browser to access the submission URL
4. Submit, then shut down Tails — it leaves nothing behind

### Moderate Safety

1. Download [Tor Browser](https://www.torproject.org/)
2. Submit from a network you don't normally use (coffee shop, library)
   — not from home or work
3. Do not log into any accounts before or after submitting in the same session

### What NOT to Do

- Do not submit from a work device or work network
- Do not submit from home if your home IP could identify you
- Do not take screenshots of the submission on a synced device
- Do not tell anyone you submitted, including via encrypted messaging apps
  (metadata can still leak)
- Do not search for the submission platform from a traceable device before submitting

---

## For Operators (Running the Server)

### Server Access

- After Cloudflare Tunnel is running, there should be **zero open inbound ports**
  on your VPS — verify with `sudo ufw status`
- All administrative access goes through Cloudflare Access SSH
- Rotate your Cloudflare Access service tokens regularly
- Enable Cloudflare audit logs for Access events

### Logging Policy

Define and document your logging retention policy explicitly:

| Log type | Recommended retention |
|---|---|
| Cloudflare edge logs (Logpush) | Disabled |
| Cloudflare Analytics | Aggregate only (no per-request) |
| Application logs (FastAPI) | Error-level only, no request bodies |
| Database | Encrypted blobs only, no metadata |
| OS auth logs (`/var/log/auth.log`) | 7 days, then purge |

### Legal Preparedness

- Know your jurisdiction's data retention laws
- Because Aegis stores no IP addresses or identifying metadata, there is
  nothing to hand over even under compulsion — but document this architecture
  clearly for your legal counsel
- Consider a canary statement (warrant canary) published regularly to signal
  if you have received legal orders you cannot disclose

### Incident Response

If you suspect the server is compromised:

1. Immediately rotate journalist keypair (generate new pair, update public key on server)
2. The old encrypted submissions remain secure — attacker cannot decrypt them
3. Take the server offline and provision a fresh VPS
4. Review Cloudflare Access logs for unauthorized admin access
5. Notify relevant parties per your organization's policy

---

## Key Rotation Schedule

| Item | Recommended interval |
|---|---|
| Journalist keypair | Annually |
| Cloudflare Access mTLS certificates | Every 90 days |
| Worker rate-limit salt | Daily (automatic in code) |
| VPS SSH keys | Every 6 months |
| Admin account passwords | Every 90 days |
