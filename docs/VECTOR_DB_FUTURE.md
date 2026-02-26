# Future Roadmap: RAG & Vector Search (pgvector)

This document outlines why and how to implement Vector Search for **Retrieval-Augmented Generation (RAG)** in the EduScan project.

## Why we need it
As EduScan grows, we need "Smart Retrieval" that goes beyond keyword matching:
1. **Semantic Formula Search**: Identifying that "solving for hypotenuse" should retrieve the *Pythagorean Theorem*.
2. **Learning Context**: Retrieving similar past problems solved by the student to provide consistent explanations.
3. **Knowledge Base**: Allowing the AI to reference large external datasets (textbooks, theorem libraries) before generating a solution.

## The Recommendation: pgvector
We should use **pgvector**, an extension for PostgreSQL, because:
- It lives inside our existing database (no new infrastructure).
- It allows atomic transactions and relationships between metadata and vectors.
- It is highly performant for the expected scale of EduScan.

---

## Installation & Setup Guide

### 1. Update Infrastructure (Docker)
Modify `backend/docker-compose.yml` to use a pgvector-enabled image:
```yaml
services:
  postgres:
    image: ankane/pgvector:v0.5.1 # Specialized image with extension installed
    ...
```

### 2. Update Backend Dependencies
Add the following to `backend/requirements.txt`:
```text
pgvector==0.2.4
```

### 3. Enable Extension
Execute this SQL in the `eduscan` database or via a migration:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### 4. Update SQLAlchemy Model
Add a vector column to the `Formula` or `ScanRecord` model:
```python
from pgvector.sqlalchemy import Vector

class Formula(Base):
    __tablename__ = "formulas"
    ...
    embedding: Mapped[Vector] = mapped_column(Vector(1536)) # Dimension for OpenAI embeddings
```

### 5. AI Integration
Use LiteLLM to generate embeddings when a new formula or problem is saved:
```python
from litellm import embedding

response = embedding(
    model="text-embedding-3-small", 
    input="The sum of the square of the legs equals..."
)
vector = response['data'][0]['embedding']
```

## Implementation Roadmap
1. **Phase 1**: Enable `pgvector` in Docker and create the extension.
2. **Phase 2**: Add `embedding` columns to `formulas` and `scan_records`.
3. **Phase 3**: Create a background task to generate embeddings for existing data.
4. **Phase 4**: Update `AIService` to perform a vector search before calling the LLM.
