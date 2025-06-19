import os
import pickle
import google.generativeai as genai
from sentence_transformers import SentenceTransformer
from datetime import datetime
import re
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# Setup Gemini
genai.configure(api_key="AIzaSyAJtQFFEG7JBwFHa6JLa4okDMXRz9_XuYs")  # replace with your key
model = genai.GenerativeModel('gemini-2.0-flash')

# Setup embedder
embedder = SentenceTransformer('all-MiniLM-L6-v2')

# Load Chat
def load_chat(path="CW 2/chat.txt"):
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    return lines

# Clean and chunk chat
def extract_messages(lines):
    pattern = re.compile(r"^(\d{1,2}/\d{1,2}/\d{2,4}),\s(\d{1,2}:\d{2})\s-\s(.*?):\s(.*)$")
    messages = []
    for line in lines:
        match = pattern.match(line.strip())
        if match:
            date, time, sender, message = match.groups()
            message = message.strip()
            if message and message not in ["<Media omitted>", "This message was deleted", "You deleted this message"]:
                messages.append(f"{sender.strip()}: {message}")
    print(f"[DEBUG] Extracted {len(messages)} messages")

    # Optional truncate to save RAM/embedding cost
    if len(messages) > 2000:
        print("[WARN] Truncating to last 2000 messages to save memory.")
        messages = messages[-2000:]
    return messages

# Embed and save
def embed_and_store(messages, out_file='embeddings.pkl'):
    if not messages:
        raise ValueError("No messages to embed. Your chat may be empty or wrongly formatted.")
    print("[DEBUG] Embedding messages...")
    embeddings = embedder.encode(messages, convert_to_tensor=False)
    with open(out_file, 'wb') as f:
        pickle.dump({'messages': messages, 'embeddings': embeddings}, f)
    print(f"[DEBUG] Saved {len(messages)} messages and {len(embeddings)} embeddings.")

# Load embeddings
def load_embeddings(path='embeddings.pkl'):
    with open(path, 'rb') as f:
        data = pickle.load(f)
    return data['messages'], data['embeddings']

# Get top N similar messages for a prompt
def get_relevant_chunks(prompt, all_messages, all_embeddings, top_n=1000):
    # if not all_embeddings:
    #     raise ValueError("Embeddings are empty. Something went wrong.")
    prompt_embedding = embedder.encode([prompt], convert_to_tensor=False)
    similarities = cosine_similarity([prompt_embedding[0]], all_embeddings)[0]
    top_indices = np.argsort(similarities)[-top_n:][::-1]
    top_messages = [all_messages[i] for i in top_indices]
    print(f"[DEBUG] Selected top {len(top_messages)} relevant chunks for the prompt.")
    return top_messages

# Prompt Gemini
def ask_gemini(prompt, context_texts):
    chat_prompt = f"""
You are a fun WhatsApp chat analyzer.
Here is some context extracted from a long chat, most relevant to the prompt:

{chr(10).join(context_texts)}

Now, respond to this prompt in a fun app-style format:
{prompt}
"""
    try:
        res = model.generate_content(chat_prompt)
        return res.text
    except Exception as e:
        print(f"[ERROR] Gemini API call failed:\n{e}")
        return "⚠️ Gemini API quota exceeded or something broke. Try again later."

# MAIN
if __name__ == "__main__":
    lines = load_chat()
    messages = extract_messages(lines)

    # Always re-embed freshly (or you can delete the `True` below to go back to conditional)
    if True or not os.path.exists('embeddings.pkl'):
        embed_and_store(messages)

    all_messages, all_embeddings = load_embeddings()

    print(f"[DEBUG] Loaded {len(all_messages)} messages and {len(all_embeddings)} embeddings.")

    
    # YOUR PROMPT HERE ↓↓↓
    test_prompt = """
Give 3 funny moments from the chat. Be specific about who said what and when.
"""

    relevant_chunks = get_relevant_chunks(test_prompt, all_messages, all_embeddings, top_n=30)
    result = ask_gemini(test_prompt, relevant_chunks)

    print("\n🔥 AI OUTPUT 🔥\n")
    print(result)