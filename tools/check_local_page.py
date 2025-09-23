import requests
r = requests.get('http://127.0.0.1:8000/index.html')
print(r.status_code)
print('Length:', len(r.text))
print('First 200 chars:\n', r.text[:200])
