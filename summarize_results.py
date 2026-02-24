
import json

with open("results.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"Total processed: {len(data)}")
for item in data:
    q_count = len(item['questions'])
    name = item.get('candidate_name', 'Unknown')
    print(f"File: {item['filename']} | Questions Found: {q_count} | Name: {name}")
