# Security Considerations

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

### Core LightlyStudio Architecture

![Core LightlyStudio Architecture](../_static/lightly_studio_architecture_overview.svg){ width="100%" }

OSS usually runs locally. Enterprise runs on a shared server with a shared datasets DB. Raw
images and videos stay in customer-controlled storage and are streamed when needed.

### Enterprise Deployment Topology

![Enterprise Deployment Topology](../_static/lightly_studio_enterprise_topology.svg){ width="100%" }

The enterprise topology is the same for Lightly-Hosted and Self-Hosted / On-Prem. The main
difference is who operates the environment, not which core components exist.

## Data Storage and External Connections

- Backend/API: LightlyStudio includes a backend API that serves the web frontend and application
  data.
- Databases: LightlyStudio uses a datasets DB for dataset metadata. Enterprise also includes a
  separate auth user DB.
- Customer integrations: LightlyStudio can work with local files and cloud buckets. Enterprise can
  centrally manage cloud storage credentials; current documentation covers AWS S3.
- External services: No OpenAI or other LLM service is documented as a core dependency here.
- Raw media: Raw images and videos are never stored on Lightly servers.

### Deployment-Specific Data Sent to or Stored by Lightly

- OSS: Only analytics data is sent to Lightly. The OSS version can also be run fully offline.
- Lightly-Hosted: To operate the service, Lightly stores analytics, user account information, and
  dataset metadata, including annotations. Raw images and videos are streamed from your storage to
  the browser when needed, but are never stored on Lightly servers.
- Self-Hosted / On-Premise: Nothing is sent to Lightly. The deployment can be fully offline and
  air-gapped.
