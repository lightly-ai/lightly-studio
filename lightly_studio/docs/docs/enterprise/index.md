# LightlyStudio Enterprise

**LightlyStudio Enterprise** is for ML teams that want a scalable and professional data management,
curation and annotation solution.

We offer it in two deployment variants:

- Hosted
- On-premise

Contact [sales@lightly.ai](mailto:sales@lightly.ai) to find the right option for your team.

## A Look Inside

<div class="ls-carousel" markdown>

![Sign in with username, password, or SSO](https://storage.googleapis.com/lightly-public/studio/docs/enterprise_login_v1.0.0.png)

![Manage multiple datasets with access control](https://storage.googleapis.com/lightly-public/studio/docs/enterprise_datasets_v1.0.0.png)

![Multi-user management with roles and permissions](https://storage.googleapis.com/lightly-public/studio/docs/enterprise_user_management_v1.0.0.png)

![Curate and search your data in the samples grid](https://storage.googleapis.com/lightly-public/studio/docs/enterprise_samples_grid_v1.0.0.png)

</div>

## Key Differences from Open-Source

| | Open-Source | Enterprise |
|---|---|---|
| **Users** | Single user | Multi-user with authentication |
| **Datasets** | Only a single dataset | Multiple datasets with access control |
| **Cloud credentials** | Local environment variables | Centrally managed by admin |
| **GUI** | Started locally via `ls.start_gui()` | Always running on the server |
| **Python API** | Direct | Same, after calling `ls.connect()` |

## Getting Started

- [Connect from Python](connect.md)
- [Security and Architecture](security.md)
- [On-Premise Deployment](on-premise.md)
- [Local Storage](local_storage.md)
- [Cloud Storage](cloud_storage/index.md)
