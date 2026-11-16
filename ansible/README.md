# CEI-InOE Ansible Deployment

Ansible playbook for deploying CEI-InOE to Intel NUC devices.

## Prerequisites

- **Control machine**: Ansible 2.14+ with Python 3.9+
- **Target NUC**: Ubuntu Server 22.04 or 24.04 with SSH access
- **Network**: Control machine can reach NUC via SSH
- **Git access**: SSH key or HTTPS credentials for the CEI-InOE repository

## Quick Start

### 1. Install Ansible Collections

```bash
cd ansible
ansible-galaxy collection install -r requirements.yml
```

### 2. Configure Inventory

Keep host aliases in `inventory/hosts.yml`. Store the real address, SSH user,
and private-key path in the encrypted vault:

```yaml
cei-nuc-01:
  ansible_host: "{{ vault_nuc_ansible_host }}"
  ansible_user: "{{ vault_nuc_ansible_user }}"
  ansible_ssh_private_key_file: "{{ vault_nuc_ssh_private_key_file }}"
```

### 3. Configure Variables

Edit `group_vars/nuc.yml` and adjust:

- `cei_inoe_repo_url`: Repository URL (SSH or HTTPS)
- `cei_inoe_version`: Git branch or tag to deploy
- `cei_inoe_cors_origins`: Allowed CORS origins (include NUC IP)
- `cei_inoe_api_port`, `cei_inoe_db_port`, `cei_inoe_grafana_port`:
  published host ports (defaults: 8000, 5432, 3000)
- Connector settings: poll intervals, lookback days, etc.

### 4. Set Secrets

Encrypt the vault file with your secrets:

```bash
# Create encrypted vault (first time)
ansible-vault create group_vars/nuc/vault.yml
```

Or edit existing vault:

```bash
ansible-vault edit group_vars/nuc/vault.yml
```

Required secrets:

```yaml
vault_nuc_ansible_host: "192.168.1.50"
vault_nuc_ansible_user: "ubuntu"
vault_nuc_ssh_private_key_file: "~/.ssh/id_ed25519"
vault_cei_inoe_db_password: "secure-db-password"
vault_cei_inoe_api_key: "secure-api-key"
vault_cei_inoe_cors_origins:
  - "http://192.168.1.50:3000"
  - "http://192.168.1.50:8000"
vault_cei_inoe_active_site: "your-site"
vault_cei_inoe_airbeld_email: "your-email@example.com"
vault_cei_inoe_airbeld_password: "airbeld-password"
# Add other connector credentials as needed
```

Use `group_vars/nuc/vault.example.yml` as the complete key checklist. The
example contains placeholders only; never put real values in it.

### Per-host active site

Set `host_active_site` in `inventory/host_vars/<host-alias>.yml` to select
the active site for that host. The filename must match its alias in
`inventory/hosts.yml`. For example:

```yaml
---
host_active_site: blue_farm
```

An example file for `cei-nuc-01` is provided; replace its `{}` with the
setting above. Add another inventory host and matching host variables file to
configure a different site, such as `lk_farm`. Available site names are defined
in `ingestor/conf/site_config.yaml` in the deployed version. If
`host_active_site` is not set, the existing `vault_cei_inoe_active_site` value
is used.

This override only applies to the active site. Other settings and credentials
still come from the shared group variables and vault; adding per-host overrides
for them requires corresponding changes to the variable mappings.

### 5. Deploy

Run the playbook:

```bash
ansible-playbook -i inventory/hosts.yml playbooks/deploy.yml \
  --ask-become-pass \
  --ask-vault-pass
```

The playbook will:
1. Install Docker Engine and Compose plugin
2. Install Git and Python dependencies
3. Create deployment directories
4. Clone the CEI-InOE repository
5. Render environment configuration
6. Start the Docker Compose stack
7. Wait for services to be healthy

### Multiple deployments on one device

Each deployment needs its own checkout directory with a distinct directory
name, and three host ports that are not in use by another deployment or
service. Docker Compose derives its project name from the directory name;
different names isolate the containers, networks and named database and
Grafana volumes. Do not set the same `COMPOSE_PROJECT_NAME` for both stacks.
Existing non-repository deployment directories may be removed by the playbook
before checkout, so choose a new, empty path.

For example, leave the first deployment at its defaults and deploy a second:

```bash
ansible-playbook -i inventory/hosts.yml playbooks/deploy.yml \
  -e cei_inoe_app_dir=/opt/cei-inoe-second \
  -e cei_inoe_api_port=8001 \
  -e cei_inoe_db_port=5433 \
  -e cei_inoe_grafana_port=3001 \
  --ask-become-pass \
  --ask-vault-pass
```

Use the same options on subsequent deployments of that instance. Ensure the
selected `cei_inoe_version` contains the corresponding Compose changes. The
ports are host-side only: PostgreSQL remains on `postgres:5432` inside each
Compose network, and API and Grafana remain on container ports 8000 and 3000.
The API health check uses the configured host port. Include the relevant
browser origins and ports in `vault_cei_inoe_cors_origins` for each instance.
Changing an existing deployment's directory or Compose project name creates
new volumes rather than moving its existing data.

### 6. Verify Deployment

After successful deployment, verify the services (replace the ports with the
configured host ports if different):

```bash
# Check health endpoint
curl http://NUC_IP:8000/health

# Check readiness
curl http://NUC_IP:8000/ready

# View API documentation
# Open in browser: http://NUC_IP:8000/docs

# View Grafana dashboards
# Open in browser: http://NUC_IP:3000
```

Test authenticated API access:

```bash
curl -H "X-API-Key: YOUR_API_KEY" http://NUC_IP:8000/api/v1/datasources
```

## Updating the Deployment

To update to a newer version:

```bash
# Update to latest main branch
ansible-playbook -i inventory/hosts.yml playbooks/deploy.yml \
  --ask-become-pass \
  --ask-vault-pass

# Or deploy a specific version
ansible-playbook -i inventory/hosts.yml playbooks/deploy.yml \
  -e cei_inoe_version=v1.2.3 \
  --ask-become-pass \
  --ask-vault-pass
```

## Managing Services on the NUC

SSH into the NUC and use Docker Compose commands:

```bash
cd /opt/cei-inoe

# View running services
docker compose -f docker-compose.dev.yml -f docker-compose.override.yml ps

# View logs
docker compose -f docker-compose.dev.yml -f docker-compose.override.yml logs -f

# View specific service logs
docker compose -f docker-compose.dev.yml -f docker-compose.override.yml logs -f api
docker compose -f docker-compose.dev.yml -f docker-compose.override.yml logs -f ingestor

# Restart services
docker compose -f docker-compose.dev.yml -f docker-compose.override.yml restart

# Stop services
docker compose -f docker-compose.dev.yml -f docker-compose.override.yml down

# Start services
docker compose -f docker-compose.dev.yml -f docker-compose.override.yml up -d
```

For another instance, change to its own checkout directory before running
these commands.

## Testing port configuration

With Ansible and the Docker Compose plugin installed, run:

```bash
ansible-playbook -i localhost, tests/ports.yml
```

This renders example deployments and checks their resolved Compose
configuration; it does not start containers.

To test per-host site selection and the vault fallback without deploying:

```bash
ansible-playbook -i tests/site_inventory/hosts.yml tests/active_site.yml
```

## Directory Structure

```
ansible/
├── README.md                          # This file
├── requirements.yml                   # Ansible collection dependencies
├── inventory/
│   └── hosts.yml                      # NUC inventory
├── group_vars/
│   ├── nuc.yml                        # Non-secret variables
│   └── nuc/
│       └── vault.yml                  # Encrypted secrets
├── templates/
│   ├── cei-inoe.env.j2                # Application environment file
│   └── docker-compose.override.yml.j2 # Compose override template
└── playbooks/
    └── deploy.yml                     # Main deployment playbook
```

## Troubleshooting

### SSH Connection Issues

If Ansible cannot connect to the NUC:

1. Verify SSH access: `ssh ubuntu@NUC_IP`
2. Check inventory file has correct IP and user
3. Ensure SSH key is in ssh-agent or use `--ask-pass`

### Docker Permission Errors

If you see Docker permission errors after deployment:

```bash
# On the NUC, log out and back in to apply group membership
exit
ssh ubuntu@NUC_IP
```

### Service Health Check Fails

If the health check times out:

1. SSH into the NUC
2. Check service status: `docker compose ps`
3. Check logs: `docker compose logs api`
4. Verify network connectivity
5. Check if the configured API host port is accessible

### Database Connection Issues

If services fail to connect to PostgreSQL:

1. Check database logs: `docker compose logs postgres`
2. Verify `.env` file has correct `DB_DSN` and `DATABASE_URL`
3. Ensure migrations completed: `docker compose logs migrations`

## Security Notes

- The `vault.yml` file should always be encrypted with `ansible-vault`
- Commit encrypted `vault.yml` so authorized machines receive it through Git
- Share the vault password through a password manager, never through Git
- Never commit an Ansible vault-password file or an SSH private key
- Never commit unencrypted secrets to version control
- Change default passwords before production deployment
- Consider restricting PostgreSQL port to localhost only
- Use strong API keys for production deployments

## Next Steps

For production deployments, consider adding:

- HTTPS reverse proxy (Nginx or Caddy)
- Tailscale for secure remote access
- UFW firewall configuration
- Automated backups for PostgreSQL
- Monitoring and alerting
- Log aggregation
