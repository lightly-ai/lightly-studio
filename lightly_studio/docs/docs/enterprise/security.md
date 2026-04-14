# Security Considerations


Lightly is committed to data security and maintains high security standards for enterprise-grade
machine learning operations.

- ISO 27001: Lightly is ISO 27001 certified, ensuring the confidentiality, integrity, and
  availability of your data through robust information security management.
- GDPR: Lightly is fully compliant with the General Data Protection Regulation (GDPR), protecting
  user privacy and upholding strict data handling standards.

## Data Sent to or Stored by Lightly

For all deployments, images and videos are never stored on Lightly servers. For some deployments, certain other data is sent to Lightly.

### OSS version

Only analytics data is sent to Lightly. However, you can run the solution offline.

### Lightly-Hosted version

Analytics, user account information, and dataset metadata including annotations are stored by Lightly. Raw images and videos are streamed from cloud storage via a Lightly server to the browser
for display. However, they are never stored on Lightly servers.

### On-Premise version

Nothing is sent to Lightly. The deployment can be fully offline or air-gapped.
