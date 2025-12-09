✅ PM Mentor — Task: Create Epic
Epic ID: CONNECTOR-100
Epic Title: Combine Connector v1 (Document Ingestion Agent)

Instructions:
Create a new Epic with the following requirements:

Epic Summary

Build the first version of the “Combine Connector”—a lightweight, read-only Docker/K8s agent that runs inside customer environments, syncs internal knowledge sources (Confluence, SharePoint, internal Git, S3/object storage), and securely pushes versioned documents into The Combine’s Knowledge Plane.

Business Rationale

Enterprise customers cannot upload or expose sensitive documents

Direct LLM access to internal shares is not acceptable

Knowledge ingestion must be secure, policy-driven, and auditable

Required for hybrid and fully on-prem deployments

Required Stories

Define the KnowledgeDocument schema (provenance, version, timestamps)

Build /documents ingestion API endpoint (auth, validation, storage)

Implement the Connector runtime container (Python or Go)

Add Git-based document ingestion (internal Git → Knowledge Plane)

Add one enterprise doc connector (Confluence or SharePoint)

Push-only ingestion mechanism with retries and authentication

Index documents into RAG store (chunking + embeddings)

Add tenant/project–scoped visibility rules

Deliverable

Full Epic document with stories, story points, and acceptance criteria.