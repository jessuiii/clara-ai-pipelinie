import urllib.request, json, os
req = urllib.request.Request(
    'https://api.groq.com/openai/v1/models', 
    headers={
        'Authorization': 'Bearer ' + os.environ.get('GROQ_API_KEY', ''),
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
)
try:
    print(json.loads(urllib.request.urlopen(req).read())['data'][0]['id'])
except urllib.error.HTTPError as e:
    print(f"HTTP Error {e.code}: {e.reason}")
    print(e.read().decode())