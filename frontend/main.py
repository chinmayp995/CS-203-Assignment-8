from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import requests

app = FastAPI()

# We cannect our backend url through this cmd
backend_url = "http://35.200.163.111:9567"

html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Home</title>
</head>
<body>
    <h1>Home</h1>
    <input size=100 type="text" id="docInput" placeholder="Enter text you wanna insert or search"><br><br>
    <button onclick="insertDocument()">Insert Document</button>
    <button onclick="searchDocument()">Search Document</button>
    <p id="output"></p>
    <script>
        async function insertDocument() {{
            let text = document.getElementById('docInput').value;
            let response = await fetch('{backend_url}/insert', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ text: text }})
            }});
            let data = await response.json();
            document.getElementById('output').innerText = JSON.stringify(data, null, 2);
        }}
        
        async function searchDocument() {{
            let query = document.getElementById('docInput').value;
            let response = await fetch('{backend_url}/search?query=' + encodeURIComponent(query));
            let data = await response.json();
            document.getElementById('output').innerText = JSON.stringify(data, null, 2);
        }}
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def read_root():
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9567)