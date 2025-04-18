#importing neccesary libraries

from fastapi import FastAPI, Request, Query, HTTPException
from elasticsearch import Elasticsearch, ConnectionError
from fastapi.middleware.cors import CORSMiddleware
import logging
import json
import os
import time

app = FastAPI()

# configuring CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://35.200.255.237:9567"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],    #methods for request
    allow_headers=["*"],
)

# configuring logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# elasticsearch configuration 
ES_HOST = "elasticsearch"     #host for the website
ES_PORT = 9200      #this is port on which website will be shown
INDEX_NAME = "myindex"
LOG_FILE = "logs.json"       # all logs will stored in this file

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
        
        # initial connection verification
        if not es.ping():
            raise ConnectionError("Failed to ping Elasticsearch")
            
        logger.info("Successfully connected to Elasticsearch")    #logging info
        return es
    except ConnectionError as e:
        logger.error(f"Elasticsearch connection failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Service Unavailable - Elasticsearch connection failed")

# initialize elasticsearch connection
es = get_es_connection()

# index management
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
            
            # inserting sample data
            sample_texts = [
                "India, officially the Republic of India,[j][21] is a country in South Asia. It is the seventh-largest country by area; the most populous country from June 2023 onwards;[22][23] and since its independence in 1947, the world's most populous democracy.[24][25][26] Bounded by the Indian Ocean on the south, the Arabian Sea on the southwest, and the Bay of Bengal on the southeast, it shares land borders with Pakistan to the west;[k] China, Nepal, and Bhutan to the north; and Bangladesh and Myanmar to the east. In the Indian Ocean, India is near Sri Lanka and the Maldives; its Andaman and Nicobar Islands share a maritime border with Thailand, Myanmar, and Indonesia.",
                "Modern humans arrived on the Indian subcontinent from Africa no later than 55,000 years ago.[28][29][30] Their long occupation, predominantly in isolation as hunter-gatherers, has made the region highly diverse, second only to Africa in human genetic diversity.[31] Settled life emerged on the subcontinent in the western margins of the Indus river basin 9,000 years ago, evolving gradually into the Indus Valley Civilisation of the third millennium BCE.[32] By 1200 BCE, an archaic form of Sanskrit, an Indo-European language, had diffused into India from the northwest.[33][34] Its hymns recorded the dawning of Hinduism in India.[35] India's pre-existing Dravidian languages were supplanted in the northern regions.[36] By 400 BCE, caste had emerged within Hinduism,[37] and Buddhism and Jainism had arisen, proclaiming social orders unlinked to heredity.[38] Early political consolidations gave rise to the loose-knit Maurya and Gupta Empires.[39] Widespread creativity suffused this era,[40] but the status of women declined,[41] and untouchability became an organized belief.[l][42] In South India, the Middle kingdoms exported Dravidian language scripts and religious cultures to the kingdoms of Southeast Asia.[43]",
                "In the early mediaeval era, Christianity, Islam, Judaism, and Zoroastrianism became established on India's southern and western coasts.[44] Muslim armies from Central Asia intermittently overran India's northern plains.[45] The resulting Delhi Sultanate drew northern India into the cosmopolitan networks of mediaeval Islam.[46] In south India, the Vijayanagara Empire created a long-lasting composite Hindu culture.[47] In the Punjab, Sikhism emerged, rejecting institutionalised religion.[48] The Mughal Empire, in 1526, ushered in two centuries of relative peace,[49] leaving a legacy of luminous architecture.[m][50] Gradually expanding rule of the British East India Company turned India into a colonial economy but consolidated its sovereignty.[51] British Crown rule began in 1858. The rights promised to Indians were granted slowly,[52][53] but technological changes were introduced, and modern ideas of education and public life took root.[54] A pioneering and influential nationalist movement, noted for nonviolent resistance, became the major factor in ending British rule.[55][56] In 1947, the British Indian Empire was partitioned into two independent dominions,[57][58][59][60] a Hindu-majority dominion of India and a Muslim-majority dominion of Pakistan. A large-scale loss of life and an unprecedented migration accompanied the partition.[61]",
                "India has been a federal republic since 1950, governed through a democratic parliamentary system. It is a pluralistic, multilingual and multi-ethnic society. India's population grew from 361 million in 1951 to over 1.4 billion in 2023.[62] During this time, its nominal per capita income increased from US$64 annually to US$2,601, and its literacy rate from 16.6% to 74%. A comparatively destitute country in 1951,[63] India has become a fast-growing major economy and hub for information technology services; it has an expanding middle class.[64] Indian movies and music increasingly influence global culture.[65] India has reduced its poverty rate, though at the cost of increasing economic inequality.[66] It is a nuclear-weapon state that ranks high in military expenditure. It has disputes over Kashmir with its neighbours, Pakistan and China, unresolved since the mid-20th century.[67] Among the socio-economic challenges India faces are gender inequality, child malnutrition,[68] and rising levels of air pollution.[69] India's land is megadiverse with four biodiversity hotspots.[70] India's wildlife, which has traditionally been viewed with tolerance in its culture,[71] is supported in protected habitats."
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

# initializing index on startup
initialize_index()

def log_message(action: str, message: str):
    #centralizing logging function
    # creating info to print logs

    log_entry = {
        "action": action,
        "message": message,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")    
    }
    try:
        with open(LOG_FILE, "r+") as f:   # opening log file
            logs = json.load(f)           # loading previous file
            logs.append(log_entry)         # inserting log
            f.seek(0)
            json.dump(logs, f, indent=4)
    except Exception as e:
        logger.error(f"Log write failed: {str(e)}")


# api endpoint to inserting document

@app.post("/insert")
async def insert_document(request: Request):
    try:
        data = await request.json()
        text = data.get("text", "").strip()
        
        if not text:       #checking text is empty or not
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


# api endpoint to search document
@app.get("/search")
def search_document(query: str = Query(..., min_length=1)):
    try:
        response = es.search(
            index=INDEX_NAME,
            query={"match": {"text": query}},
            size=10
        )
          
        #extracting relevant information
        results = [{"id": hit["_id"], "text": hit["_source"]["text"]} 
                 for hit in response["hits"]["hits"]]
        
        log_message("SEARCH", f"Query: '{query}' returned {len(results)} results")
        return {"results": results} if results else {"message": "No matches found"}
        
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        return {"error": "Search operation failed"}, 500


#entry point for running the FastAPI application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9567)
