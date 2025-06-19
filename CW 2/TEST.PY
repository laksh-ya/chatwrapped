import os
import pickle
import google.generativeai as genai
from sentence_transformers import SentenceTransformer
from datetime import datetime
import re

# Setup Gemini
genai.configure(api_key="YOUR_GEMINI_API_KEY")  # replace

model = genai.GenerativeModel('gemini-pro')
embedder = SentenceTransformer('all-MiniLM-L6-v2')

# Load Chat
def load_chat(path='chat.txt'):
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    return lines

# Clean and chunk chat
def extract_messages(lines):
    pattern = re.compile(r"^\d{1,2}/\d{1,2}/\d{2,4}, \d{1,2}:\d{2}\s?[apAP][mM]? - (.*?): (.*)$")
    messages = []
    for line in lines:
        match = pattern.match(line.strip())
        if match:
            sender, message = match.groups()
            messages.append(f"{sender.strip()}: {message.strip()}")
    return messages

# Embed and save
def embed_and_store(messages, out_file='embeddings.pkl'):
    embeddings = embedder.encode(messages, convert_to_tensor=False)
    with open(out_file, 'wb') as f:
        pickle.dump({'messages': messages, 'embeddings': embeddings}, f)
    print(f"Saved {len(messages)} embeddings.")

# Load embeddings
def load_embeddings(path='embeddings.pkl'):
    with open(path, 'rb') as f:
        data = pickle.load(f)
    return data['messages'], data['embeddings']

# Prompt Gemini
def ask_gemini(prompt, context_texts):
    chat_prompt = f"""
You are a fun WhatsApp chat analyzer.
Here is some conversation context from a long chat:

{chr(10).join(context_texts[:40])}  # truncate for token limit

Now, respond to this prompt in a fun app-style format:
{prompt}
"""
    res = model.generate_content(chat_prompt)
    return res.text

# Main
if __name__ == "__main__":
    lines = load_chat()
    messages = extract_messages(lines)

    if not os.path.exists('embeddings.pkl'):
        embed_and_store(messages)

    messages, _ = load_embeddings()

    # ONE TEST PROMPT
    test_prompt = """
A paragraph about the whole convo: what the chat mostly revolves around and what the range of topics are. Write it in a casual app-style vibe.
"""

    result = ask_gemini(test_prompt, messages)
    print("\n🔥 AI OUTPUT 🔥\n")
    print(result)