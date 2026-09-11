# Hardware Requirements

The Python client requirements apply to both LightlyStudio OSS and the Python
client used with Enterprise.

## Python Client Requirements

| Resource | Minimum | Recommended |
|---|---|---|
| CPU | 4 cores | 8-core x86 CPU (non-ARM) |
| System memory | 8 GB | 16 GB |
| Free disk storage | 10 GB | 40 GB |
| Operating system | macOS, Windows, or Linux | Windows or Linux |
| CPU architecture | x86 or ARM | x86 (non-ARM) |
| GPU | Not required | NVIDIA CUDA-compatible GPU with CUDA 12 |

For connection setup, see [Connect from Python](connect.md).

## Additional On-Premise Requirements

These requirements apply to the Enterprise on-premise deployment host, which
runs the LightlyStudio services and databases. They are additional to the
Python client requirements above and do not apply to Lightly-hosted Enterprise.

| Resource | Minimum | Recommended |
|---|---|---|
| CPU |  8 cores |  8 cores |
| System memory | 16 GB | 32 GB |
| Free disk storage | 40 GB | 60 GB |
| Dataset size | Below 250,000 samples | 250,000–10 million samples |
| GPU | Not required | CUDA-compatible GPU |

The on-premise host also needs a supported container runtime and network access
for Python clients and browsers. See [On-Premise Deployment](on-premise.md) for
deployment details.
