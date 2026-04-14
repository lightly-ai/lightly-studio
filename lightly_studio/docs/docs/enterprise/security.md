# Security Considerations

Lightly is committed to data security and maintains high security standards for
enterprise-grade machine learning operations.

### ISO 27001

Lightly is ISO 27001 certified, ensuring the confidentiality, integrity, and
availability of your data through robust information security management.

### GDPR

Lightly is fully compliant with the General Data Protection Regulation (GDPR),
protecting user privacy and upholding strict data handling standards.




## Which Data Is Sent to Lightly?

For all deployments, images and videos always stay on your infrastructure and are never stored on
Lightly servers. For some deployments, certain other data is sent to Lightly.

### OSS version

Only analytics data is sent to Lightly. However, you can run the solution offline.

### Lightly-Hosted version

User account information and the dataset metadata in the database are stored on Lightly
servers.
Raw images and videos are streamed from cloud storage via a Lightly server to the browser
for display. However, they are never stored on Lightly servers.

### On-Premise version
No data is sent to Lightly. You can run the solution completely offline/air-gapped.
