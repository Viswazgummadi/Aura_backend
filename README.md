# Aura Backend

Backend service for the Aura Personal Assistant, built with FastAPI, LangChain, and PostgreSQL.

## Setup

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Environment Variables**:
    Create a `.env` file in this directory with the following variables:

    | Variable | Description |
    | :--- | :--- |
    | `GOOGLE_API_KEY` | Key for Google Gemini API. |
    | `LANGCHAIN_API_KEY` | Optional. For LangSmith tracing. |
    | `LANGCHAIN_TRACING_V2` | Set to `true` to enable tracing. |
    | `LANGCHAIN_PROJECT` | Project name for LangSmith. |
    | `POSTGRES_USER` | DB User (default: postgres). |
    | `POSTGRES_PASSWORD` | DB Password (default: password). |
    | `POSTGRES_DB` | DB Name (default: aura). |
    | `POSTGRES_SERVER` | DB Host (default: localhost or db). |

3.  **Run Locally**:
    ```bash
    uvicorn app.main:app --reload
    ```

## Docker
To run with Docker, ensure `POSTGRES_SERVER` is set correctly to the container name if using the compose stack.
