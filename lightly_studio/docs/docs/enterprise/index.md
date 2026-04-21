# LightlyStudio Enterprise

**LightlyStudio Enterprise** is the multi-user, multi-dataset version of LightlyStudio.

All features of the open-source Python API work the same way once you are connected to an
enterprise instance.

Contact [sales@lightly.ai](mailto:sales@lightly.ai) to learn more about LightlyStudio Enterprise.

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
- [Cloud Storage](cloud_storage/index.md)
