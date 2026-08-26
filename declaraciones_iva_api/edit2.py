import re

with open('app/routers/procesamiento.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Fix the decoding and unwrap dteJson
decode_block = '''
        content = await file.read()
        try:
            try:
                text = content.decode('utf-8')
            except UnicodeDecodeError:
                text = content.decode('latin-1')
                
            dte_json = json.loads(text)
            if "dteJson" in dte_json and isinstance(dte_json["dteJson"], dict):
                dte_json = dte_json["dteJson"]
'''
code = re.sub(r'content = await file\.read\(\)\s+try:\s+dte_json = json\.loads\((?:content|text)\)', decode_block.strip() + '\n', code)

# We also need to fix the second json.loads if there's any.
# Let's check how many occurrences of content = await file.read() there are.
