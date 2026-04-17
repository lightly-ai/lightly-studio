# On-Premise Deployment

The on-premise deployment model is for teams that want to run LightlyStudio Enterprise
on their own infrastructure.This gives you full control over the deployment, data
storage, and security. You can run it fully offline or air-gapped if needed.

## Overview of On-Premise Architecture

In an on-premise deployment:

- `Lightly Proxy` is the single external entry point.
- `Auth Service`, `Workspace GUI`, and `Studio App` run behind that entry point.
- The datasets database runs as a separate PostgreSQL service.

For the user-facing security and architecture overview, see [Security Considerations](security.md).

## Service Layout

![Self-Hosted Service Layout](../_static/lightly_studio_self_hosted_service_layout.svg){ width="100%" }

- `Lightly Proxy` exposes the deployment.
- `Auth Service` handles authentication.
- `Workspace GUI` provides the login, datasets, and admin pages.
- `Studio App` provides the core application.
- `Datasets DB` stores enterprise dataset metadata in PostgreSQL.

