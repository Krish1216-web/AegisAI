# AegisAI Backend Portal

This is the FastAPI backend service for **AegisAI**, a multi-agent AI Operating System.

## Project Setup

### Prerequisites
- Python 3.12+
- PostgreSQL
- Redis
- Qdrant

### Installation
1. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy the environment variables template and configure your keys:
   ```bash
   cp .env.example .env
   ```

### Execution
Run the development server locally:
```bash
python app/main.py
```
Or use Uvicorn directly:
```bash
uvicorn app.main:app --reload
```
The interactive API documentation will be available at:
- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)
