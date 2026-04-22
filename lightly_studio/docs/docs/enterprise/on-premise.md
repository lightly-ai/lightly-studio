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

For the user-facing security and architecture overview, see [Security and Architecture](security.md).

