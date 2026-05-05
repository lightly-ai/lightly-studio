# Security and Architecture

Lightly is designed for secure enterprise-grade machine learning workflows. Across all deployment
models, raw images and videos are never stored on Lightly servers.

## Certifications

For the latest legal, privacy, and compliance information, see
[Lightly Legal: Privacy & Security](https://lightly.ai/legal).

- ISO 27001: Lightly is ISO 27001 certified, ensuring the confidentiality, integrity, 
  and availability of your data through robust information security management.
- GDPR: Lightly is fully compliant with the General Data Protection Regulation (GDPR),
  protecting user privacy and upholding strict data handling standards.

## Architecture Overview

The diagrams below show the shared architecture and the enterprise topology.

### Core LightlyStudio Architecture

![Core LightlyStudio Architecture](../_static/lightly_studio_architecture_overview.svg){ width="100%" }

This shows the shared architecture of OSS and Enterprise.

- A python script indexes data and writes to the datasets database.
- The LightlyStudio Core App provides the API and serves the frontend. It accesses the datasets database to read and write dataset metadata, annotations, tags, captions, and embeddings. It also streams the raw images and videos from your storage to the browser when needed, but never stores them on Lightly servers.

### Enterprise Deployment Topology

![Enterprise Deployment Topology](../_static/lightly_studio_enterprise_topology.svg){ width="100%" }

In the enterprise version, there additionally is a authentication proxy in front of the Core App. The proxy handles authentication and access control for multiple users and datasets.

If you operate your own deployment, see [On-Premise Deployment](on-premise.md) for an in-depth architecture overview.

## Where Computation Happens

- Data ingestion, indexing, and embedding generation always run locally on the machine where the Python script runs, never on a Lightly server.
- In OSS, this is usually the same script that later starts the UI with `ls.start_gui()`.
- In Enterprise, admin Python scripts call `ls.connect()` and then use the same Python API against the enterprise datasets database. See [Connect from Python](connect.md) for details.


## Deployment-Specific Data Sent to or Stored by Lightly

- OSS: Only analytics data is sent to Lightly. The OSS version can also be run fully offline.
- Lightly-Hosted: To operate the service, Lightly stores analytics, user account information, and
  dataset metadata, including annotations. Raw images and videos are streamed from your storage to
  the browser when needed, but are never stored on Lightly servers.
- On-Premise: Nothing is sent to Lightly. The deployment can be fully offline and
  air-gapped.
