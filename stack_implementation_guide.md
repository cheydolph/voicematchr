# VoiceMatchr Stack Implementation Guide

This is the authoritative deployment reference for VoiceMatchr. It describes
the production arrangement actually serving
[voicematchr.fiestaszn.com](https://voicematchr.fiestaszn.com/):
Kokoro-TTS as a TrueNAS SCALE catalog app, the VoiceMatchr stack managed via
Dockge on the same host, and external HTTPS access through a Cloudflare Tunnel.

## Architecture

Both stacks run on one TrueNAS SCALE host and share a single external Docker
network, `kokoro-net`:

- `voicematchr-service` addresses Kokoro by container DNS name
  (`http://kokoro-proxy:8881`) rather than a LAN IP, so `KOKORO_BASE_URL`
  carries no host-address dependency.
- External reachability comes from a `cloudflared` container inside the
  VoiceMatchr compose project. The connector dials out to Cloudflare's edge;
  no inbound port forward, static IP, or DDNS client is required.
- Kokoro's nginx allowlist proxy (`nginx-kokoro.conf`, port 8881) stays
  Docker-internal. It is never exposed through the tunnel, and the browser
  never contacts Kokoro directly.

## Prerequisites

- SSH access to the TrueNAS SCALE host with sudo.
- A ZFS dataset path for persistent data (`/mnt/tank/...` below; adjust the
  pool name as needed).
- A Cloudflare account with the target domain's DNS on Cloudflare.
- TrueNAS SCALE 25.04 or later for the Custom App "Install via YAML" path. On
  older releases, run `kokoro-compose.yml` over SSH with `docker compose`
  instead; the running state is identical.
- GPU passthrough enabled for Apps, with `nvidia-smi` succeeding on the host.

## Phase 0: host preparation

```bash
# Shared network. Both compose files declare it external, so compose refuses
# to start either stack until it exists.
sudo docker network create kokoro-net

# Kokoro's persistent paths, matching kokoro-compose.yml's volume mounts.
sudo mkdir -p /mnt/tank/kokoro/models /mnt/tank/kokoro/nginx
```

Upload `nginx-kokoro.conf` to `/mnt/tank/kokoro/nginx/nginx-kokoro.conf`.

## Phase 1: Kokoro-TTS as a catalog app

1. Open **Apps**, then **Discover Apps**, then **Custom App**.
2. Select the **Install via YAML** tab and paste `kokoro-compose.yml`
   unmodified.
3. If the importer strips the `deploy:` GPU reservation block, reapply the GPU
   through the Apps GUI resource settings after import.
4. Deploy, then verify from the host:

```bash
curl http://localhost:8881/health
curl http://localhost:8881/v1/audio/voices
```

The first `/v1/audio/speech` call is slow: `DOWNLOAD_MODEL=true` pulls the
model on cold start. Issue one synthesis call after deploy so the model is
warm before any learner or seeding script hits it.

## Phase 2: install Dockge

Bootstrap Dockge once over SSH; every later stack is managed through its UI.

```bash
sudo mkdir -p /mnt/tank/dockge/data /mnt/tank/dockge/stacks
cd /mnt/tank/dockge
sudo tee dockge-compose.yml > /dev/null << 'EOF'
services:
  dockge:
    image: louislam/dockge:1
    restart: unless-stopped
    ports:
      - "5001:5001"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - /mnt/tank/dockge/data:/app/data
      - /mnt/tank/dockge/stacks:/opt/stacks
    environment:
      - DOCKGE_STACKS_DIR=/opt/stacks
EOF
sudo docker compose -f dockge-compose.yml up -d
```

Confirm at `http://<truenas-lan-ip>:5001`.

## Phase 3: prepare the VoiceMatchr stack

```bash
sudo mkdir -p /mnt/tank/dockge/stacks/voicematchr
```

Clone the repository into that directory, or point Dockge's Compose-from-Git
option at the
[VoiceMatchr repository](https://github.com/cheydolph/voicematchr.git).

`voicematchr-service` runs as non-root UID 1001. The bind-mounted `data/`
directory must be owned by that UID on the host before first start, or
startup fails with `sqlite3.OperationalError: unable to open database file`:

```bash
sudo chown -R 1001:1001 /mnt/tank/dockge/stacks/voicematchr/data
```

If the dataset uses TrueNAS's default NFSv4 ACLs, confirm with
`getfacl data/` that the ownership took effect; an inherited ACL entry can
override a bare `chown`. If so, set the dataset's permission type to Unix
under **Storage**, then **Edit Permissions**, or add an explicit ACL entry for
UID 1001.

Create `.env` alongside `docker-compose.yml`:

```bash
KOKORO_BASE_URL=http://kokoro-proxy:8881
DB_PATH=/data/voicematchr.db
RECORDINGS_DIR=/data/recordings
CORS_ALLOW_ORIGINS=https://voicematchr.fiestaszn.com
CLOUDFLARE_TUNNEL_TOKEN=<from Phase 4>
```

The `kokoro-proxy` name resolves only because both stacks joined `kokoro-net`
in Phase 0/1. Confirm the service name with
`docker network inspect kokoro-net` if the YAML import renamed anything.

## Phase 4: configure the Cloudflare Tunnel

1. In the Cloudflare dashboard, open **Zero Trust**, then **Networks**, then
   **Tunnels**, and create a tunnel named `voicematchr` with the Cloudflared
   connector type.
2. Copy only the token value from the displayed connector command into
   `CLOUDFLARE_TUNNEL_TOKEN` in `.env`. The compose service runs
   `cloudflared tunnel run` and reads the token from the environment.
3. On the tunnel's **Public Hostname** tab, map the public hostname to
   Service Type `HTTP`, URL `nginx:80`. Cloudflare creates the CNAME record
   automatically.

## Phase 5: deploy via Dockge

1. Open the `voicematchr` stack in Dockge and confirm `.env` sits beside
   `docker-compose.yml`.
2. Deploy. First deploy builds `voicematchr-service` and `frontend` from
   source and takes several minutes.
3. Confirm all five containers reach a running state (the `seed` container
   exits with status 0 once it finishes; that is expected, not a failure),
   and that `voicematchr-service` reports healthy.
4. Run the smoke test:

```bash
python3 scripts/smoke_test.py --base-url http://localhost:8080/api
```

## Phase 6: verification

From the TrueNAS host, independent of the tunnel:

```bash
curl http://localhost:3939/health
curl http://localhost:8080/
```

From outside the LAN, on a cellular connection rather than the host's own
network (testing from the same LAN produces false positives when the tunnel
is misconfigured):

```bash
curl -I https://voicematchr.fiestaszn.com/
curl https://voicematchr.fiestaszn.com/api/health
python3 scripts/smoke_test.py
```

If `/api/health` fails while `/` succeeds, the fault is in `nginx.conf`'s
`/api/` block or the service, not the tunnel. If both fail, read
`docker compose logs cloudflared` first.

## Operational notes

- `kokoro-net` must exist before either stack starts. After a host reboot,
  `sudo docker network create kokoro-net` is idempotent and safe to run
  unconditionally before bringing stacks up.
- The allowlist proxy on 8881 must never be published to the WAN. It is
  reachable only from `kokoro-net`, which is the intended boundary.
- Dockge and TrueNAS Apps drive the same host `dockerd`; seeing both sets of
  containers in `docker compose ps -a` is expected, not a conflict.
- Smoke-test write-path runs create database rows marked with `smoke-test`
  demographics; filter these out of any evaluation export.
