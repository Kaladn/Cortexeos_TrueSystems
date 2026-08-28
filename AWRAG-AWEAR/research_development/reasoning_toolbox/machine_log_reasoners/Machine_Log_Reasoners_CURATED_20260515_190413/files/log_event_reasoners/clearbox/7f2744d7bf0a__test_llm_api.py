"""Quick test of LLM API"""
import requests
import json

url = "http://localhost:11435/api/generate"
payload = {
    "model": "qwen2.5:1.5b",
    "prompt": "Say hello in one sentence.",
    "stream": False,
    "max_tokens": 50
}

print("Testing LLM API...")
print(f"URL: {url}")
print(f"Payload: {json.dumps(payload, indent=2)}")
print("\nSending request...\n")

try:
    response = requests.post(url, json=payload, timeout=30)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ Success!")
        print(f"Response text: {data.get('response', 'NO RESPONSE FIELD')}")
    else:
        print(f"\n❌ Error {response.status_code}")
        
except Exception as e:
    print(f"\n❌ Exception: {e}")
