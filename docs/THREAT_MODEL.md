# Aegis — Threat Model

## Assets Being Protected

1. **Submitter identity** — who submitted
2. **Submission content** — what was submitted
3. **Platform availability** — the ability to receive submissions

---

## Adversary Classes

### Tier 1 — Passive Observer (ISP / Network-level)
- **Capability**: Can see that a connection was made to Cloudflare's edge IPs
- **Cannot see**: Content (TLS), destination beyond Cloudflare, submitter identity
- **Mitigation**: Tor Browser usage removes even this — connection appears to go to Tor relay

### Tier 2 — Cloudflare (Infrastructure Provider)
- **Capability**: Sees raw IP, full request at the edge before Worker runs
- **Cannot see**: Decrypted content (encrypted at origin with journalist key)
- **Mitigation**: Worker strips IP before forwarding. Logpush should be disabled.
  Cloudflare's privacy policy and Project Galileo protections apply.
- **Residual risk**: Cloudflare could theoretically log pre-Worker data. This is a
  trust assumption — acknowledged and accepted for most threat models.

### Tier 3 — Server Compromise (Attacker gains access to origin)
- **Capability**: Can read database, see incoming requests
- **Cannot see**: Plaintext content (encrypted with journalist public key)
- **Cannot do**: Decrypt submissions without journalist private key
- **Mitigation**: Hybrid encryption ensures server never holds decryption capability.
  Cloudflare Tunnel means no open ports to scan/attack directly.

### Tier 4 — Legal Compulsion (Court order / Law enforcement)
- **Capability**: Can compel server operator to produce data
- **Cannot produce**: Submitter identity (not stored), plaintext content (not stored)
- **Mitigation**: No-logging architecture means there is nothing to hand over.
  Server holds only encrypted blobs and UUIDs.
- **Residual risk**: Cloudflare may receive legal orders for edge-level logs.
  Tor usage by submitters mitigates this.

### Tier 5 — State-Sponsored / Nation State
- **Capability**: Traffic analysis at scale, endpoint compromise, legal coercion
- **Mitigation**: Tor + Tails OS for submitters, air-gapped key management,
  Cloudflare's geopolitical position as a US company
- **Residual risk**: Sophisticated endpoint attacks (malware on submitter device)
  are outside the scope of this platform

---

## Trust Assumptions

| Component | What we trust them with | Mitigation if trust broken |
|---|---|---|
| Cloudflare | Edge-level IP visibility | Submitters use Tor |
| VPS provider | Server hardware access | FDE + encrypted DB |
| Journalist | Private key security | Air-gapped storage, passphrase |
| Submitter's device | Not compromised | Recommend Tails OS |

---

## Out of Scope

- **Submitter endpoint security**: If the submitter's device is compromised (keylogger, malware), no server-side architecture helps
- **Physical coercion**: Compelling the journalist to use the private key
- **Metadata correlation over time**: Long-term traffic analysis by nation-state adversaries
- **Social engineering**: Deceiving journalists or operators

---

## Recommendations for High-Risk Deployments

- Provide a `.onion` address (Tor Hidden Service) so even the connection to Cloudflare is hidden
- Publish your public key on a separate, independently verifiable channel (Keybase, etc.)
- Rotate journalist keypairs annually
- Consider multi-journalist key splitting (Shamir's Secret Sharing) for very sensitive operations
