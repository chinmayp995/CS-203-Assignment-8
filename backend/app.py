from fastapi import FastAPI, Request, Query, HTTPException
from elasticsearch import Elasticsearch, ConnectionError
from fastapi.middleware.cors import CORSMiddleware
import logging
import json
import os
import time

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://35.200.255.237:9567"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Elasticsearch configuration
ES_HOST = "elasticsearch"
ES_PORT = 9200
INDEX_NAME = "myindex"
LOG_FILE = "logs.json"

def get_es_connection():
    """Create and verify Elasticsearch connection"""
    try:
        es = Elasticsearch(
            [f"http://{ES_HOST}:{ES_PORT}"],
            request_timeout=30,
            max_retries=3,
            retry_on_timeout=True,
            sniff_on_start=False,
            sniff_on_node_failure=False
        )
        
        # Initial connection verification
        if not es.ping():
            raise ConnectionError("Failed to ping Elasticsearch")
            
        logger.info("Successfully connected to Elasticsearch")
        return es
    except ConnectionError as e:
        logger.error(f"Elasticsearch connection failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Service Unavailable - Elasticsearch connection failed")

# Initialize Elasticsearch connection
es = get_es_connection()

# Index management
def initialize_index():
    """Create index if not exists with proper mappings"""
    if not es.indices.exists(index=INDEX_NAME):
        try:
            es.indices.create(
                index=INDEX_NAME,
                body={
                    "mappings": {
                        "properties": {
                            "id": {"type": "keyword"},
                            "text": {"type": "text"}
                        }
                    }
                }
            )
            logger.info(f"Created index {INDEX_NAME}")
            
            # Insert sample data
            sample_texts = [
                "India, officially the Republic of India...",
                "Modern humans arrived on the Indian subcontinent...",
                "In the early mediaeval era, Christianity...",
                "India has been a federal republic since 1950..."
            ]
            
            for i, text in enumerate(sample_texts):
                es.index(
                    index=INDEX_NAME,
                    id=i+1,
                    document={"id": str(i+1), "text": text}
                )
            logger.info("Inserted initial sample documents")
            
        except Exception as e:
            logger.error(f"Index initialization failed: {str(e)}")
            raise HTTPException(status_code=500, detail="Index creation failed")

# Initialize index on startup
initialize_index()

def log_message(action: str, message: str):
    """Centralized logging function"""
    log_entry = {
        "action": action,
        "message": message,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    try:
        with open(LOG_FILE, "r+") as f:
            logs = json.load(f)
            logs.append(log_entry)
            f.seek(0)
            json.dump(logs, f, indent=4)
    except Exception as e:
        logger.error(f"Log write failed: {str(e)}")

@app.post("/insert")
async def insert_document(request: Request):
    try:
        data = await request.json()
        text = data.get("text", "").strip()
        
        if not text:
            log_message("ERROR", "Empty text in insert request")
            return {"error": "Text field is required"}, 400
            
        es.index(
            index=INDEX_NAME,
            document={"text": text},
            refresh=True
        )
        log_message("INSERT", f"Inserted document: {text[:50]}...")
        return {"message": "Document inserted successfully"}
        
    except Exception as e:
        logger.error(f"Insert error: {str(e)}")
        return {"error": "Document insertion failed"}, 500

@app.get("/search")
def search_document(query: str = Query(..., min_length=1)):
    try:
        response = es.search(
            index=INDEX_NAME,
            query={"match": {"text": query}},
            size=10
        )
        
        results = [{"id": hit["_id"], "text": hit["_source"]["text"]} 
                 for hit in response["hits"]["hits"]]
        
        log_message("SEARCH", f"Query: '{query}' returned {len(results)} results")
        return {"results": results} if results else {"message": "No matches found"}
        
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        return {"error": "Search operation failed"}, 500

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9567)
