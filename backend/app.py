from fastapi import FastAPI, Request, Query
from elasticsearch import Elasticsearch
from fastapi.middleware.cors import CORSMiddleware
import time
import logging
import json
import os

app = FastAPI()

# Enable CORS so frontend can communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://34.100.226.225:9567"],  # Replace with frontend's external IP for security
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Logger setup
LOG_FILE = "logs.json" # docker volume vaparyacha aahey

# Create log file if it does not exist
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, "w") as f:
        json.dump([], f)

def log_message(action, message):
    """Logs a message into logs.json."""
    log_entry = {
        "action": action,
        "message": message,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Read existing logs
    with open(LOG_FILE, "r") as f:
        logs = json.load(f)
    
    # Append new log entry
    logs.append(log_entry)
    
    # Write back to the log file
    with open(LOG_FILE, "w") as f:
        json.dump(logs, f, indent=4)

# Connect to Elasticsearch container running on the same Docker network
es = None
for _ in range(10): 
    try:
        es = Elasticsearch(["http://127.0.0.1:9200"])
        if es.ping():
            print("Connected to Elasticsearch")
            log_message("INFO", "Connected to Elasticsearch")
            break
    except Exception as e:
        print("Waiting for Elasticsearch...", str(e))
        log_message("ERROR", f"Waiting for Elasticsearch... {str(e)}")
        time.sleep(10)

if es is None or not es.ping():
    log_message("ERROR", "Could not connect to Elasticsearch")
    raise Exception("Could not connect to Elasticsearch")

# Ensure index exists
index_name = "myindex"
if not es.indices.exists(index=index_name):
    es.indices.create(
        index=index_name,
        body={
            "mappings": {
                "properties": {
                    "id": {"type": "keyword"},
                    "text": {"type": "text"}
                }
            }
        }
    )
    log_message("INFO", f"Created index {index_name}")

    # these are first 4 paara of India
    wiki_texts = [
        "India, officially the Republic of India,[j][21] is a country in South Asia. It is the seventh-largest country by area; the most populous country from June 2023 onwards;[22][23] and since its independence in 1947, the world's most populous democracy.[24][25][26] Bounded by the Indian Ocean on the south, the Arabian Sea on the southwest, and the Bay of Bengal on the southeast, it shares land borders with Pakistan to the west;[k] China, Nepal, and Bhutan to the north; and Bangladesh and Myanmar to the east. In the Indian Ocean, India is near Sri Lanka and the Maldives; its Andaman and Nicobar Islands share a maritime border with Thailand, Myanmar, and Indonesia.",
        "Modern humans arrived on the Indian subcontinent from Africa no later than 55,000 years ago.[28][29][30] Their long occupation, predominantly in isolation as hunter-gatherers, has made the region highly diverse, second only to Africa in human genetic diversity.[31] Settled life emerged on the subcontinent in the western margins of the Indus river basin 9,000 years ago, evolving gradually into the Indus Valley Civilisation of the third millennium BCE.[32] By 1200 BCE, an archaic form of Sanskrit, an Indo-European language, had diffused into India from the northwest.[33][34] Its hymns recorded the dawning of Hinduism in India.[35] India's pre-existing Dravidian languages were supplanted in the northern regions.[36] By 400 BCE, caste had emerged within Hinduism,[37] and Buddhism and Jainism had arisen, proclaiming social orders unlinked to heredity.[38] Early political consolidations gave rise to the loose-knit Maurya and Gupta Empires.[39] Widespread creativity suffused this era,[40] but the status of women declined,[41] and untouchability became an organized belief.[l][42] In South India, the Middle kingdoms exported Dravidian language scripts and religious cultures to the kingdoms of Southeast Asia.[43]",
        "In the early mediaeval era, Christianity, Islam, Judaism, and Zoroastrianism became established on India's southern and western coasts.[44] Muslim armies from Central Asia intermittently overran India's northern plains.[45] The resulting Delhi Sultanate drew northern India into the cosmopolitan networks of mediaeval Islam.[46] In south India, the Vijayanagara Empire created a long-lasting composite Hindu culture.[47] In the Punjab, Sikhism emerged, rejecting institutionalised religion.[48] The Mughal Empire, in 1526, ushered in two centuries of relative peace,[49] leaving a legacy of luminous architecture.[m][50] Gradually expanding rule of the British East India Company turned India into a colonial economy but consolidated its sovereignty.[51] British Crown rule began in 1858. The rights promised to Indians were granted slowly,[52][53] but technological changes were introduced, and modern ideas of education and public life took root.[54] A pioneering and influential nationalist movement, noted for nonviolent resistance, became the major factor in ending British rule.[55][56] In 1947, the British Indian Empire was partitioned into two independent dominions,[57][58][59][60] a Hindu-majority dominion of India and a Muslim-majority dominion of Pakistan. A large-scale loss of life and an unprecedented migration accompanied the partition.[61]",
        "India has been a federal republic since 1950, governed through a democratic parliamentary system. It is a pluralistic, multilingual and multi-ethnic society. India's population grew from 361 million in 1951 to over 1.4 billion in 2023.[62] During this time, its nominal per capita income increased from US$64 annually to US$2,601, and its literacy rate from 16.6% to 74%. A comparatively destitute country in 1951,[63] India has become a fast-growing major economy and hub for information technology services; it has an expanding middle class.[64] Indian movies and music increasingly influence global culture.[65] India has reduced its poverty rate, though at the cost of increasing economic inequality.[66] It is a nuclear-weapon state that ranks high in military expenditure. It has disputes over Kashmir with its neighbours, Pakistan and China, unresolved since the mid-20th century.[67] Among the socio-economic challenges India faces are gender inequality, child malnutrition,[68] and rising levels of air pollution.[69] India's land is megadiverse with four biodiversity hotspots.[70] India's wildlife, which has traditionally been viewed with tolerance in its culture,[71] is supported in protected habitats."
    ]

    for i, text in enumerate(wiki_texts):
        es.index(index=index_name, id=i + 1, body={"id": str(i + 1), "text": text})
        log_message("INSERT", f"Inserted sample document {i + 1}")

@app.post("/insert")
async def insert_document(request: Request):
    data = await request.json()
    text = data.get("text", "")
    
    if not text:
        log_message("ERROR", "Insert request failed: Text field is missing")
        return {"error": "Text field is required"}
    
    doc = {"text": text}
    es.index(index=index_name, body=doc)
    
    log_message("INSERT", f"Inserted document: {text}")
    return {"message": "Inserted successfully!"}

@app.get("/search")
def search_document(query: str = Query(..., min_length=1)):
    response = es.search(index=index_name, body={"query": {"match": {"text": query}}})
    
    if response["hits"]["hits"]:
        log_message("SEARCH", f"Query: {query}, Results: {len(response['hits']['hits'])}")
        return response["hits"]["hits"]
    else:
        log_message("SEARCH", f"Query: {query}, No matches found")
        return {"message": "No match found"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9567)