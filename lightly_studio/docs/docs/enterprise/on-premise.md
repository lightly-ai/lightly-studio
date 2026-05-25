# On-Premise Deployment

The on-premise deployment model is for teams that want to run LightlyStudio Enterprise
on their own infrastructure. This gives you full control over the deployment, data
storage, and security. You can run it fully offline or air-gapped if needed.

## Components of the On-Premise Deployment

![On-Premise Service Layout](../_static/lightly_studio_on_premise_service_layout.svg){ width="100%" }

- `Lightly Proxy` exposes the deployment.
- `Authentication Service` handles authentication.
- `Workspace UI` provides the login, datasets, and admin pages.
- `Studio App` provides the core application including the backend API and frontend.
- `Datasets Database` stores enterprise dataset metadata in PostgreSQL.
- `Users Database` stores user accounts in SQLite on the `auth_data` volume.

### Datasets database migrations

On startup, the Studio backend applies PostgreSQL schema changes automatically:

- **New deployments** on an empty database run `upgrade head`; schema comes from the Alembic revision chain shipped in the container image.
- **Upgrades** from a release that already uses Alembic run pending revisions in order (`upgrade head`) using the same revision chain.

Product version labels (for example v5 → v10) map to Alembic revision ids in release notes; the `alembic_version` table stores the current revision id, not the product version string.

For the user-facing security and architecture overview, see [Security and Architecture](security.md).

For on-premise local disk or NAS/shared mounts used with `ls.connect()`, see
[Local Storage](local_storage.md).
