from ollama import Client
import time

print("Testing direct Python -> Ollama connection...")
client = Client(host='http://127.0.0.1:11434')

start_time = time.time()
try:
    response = client.chat(
        model='phi3:mini', 
        messages=[{'role': 'user', 'content': 'Respond with exactly one word: Hello'}]
    )
    elapsed = time.time() - start_time
    print(f"✅ Success! Ollama replied in {elapsed:.2f} seconds.")
    print(f"Response: {response['message']['content']}")
except Exception as e:
    print(f"❌ Connection Failed: {e}")