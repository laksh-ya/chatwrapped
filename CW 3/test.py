import streamlit as st
import re
import datetime
import json
import google.generativeai as genai

# --- Helper functions from strip.py ---

def reconstruct_messages(raw_lines):
    chat = []
    current = ""
    # Regex to identify the start of a new message
    pattern = re.compile(r"^\d{1,2}/\d{1,2}/\d{2,4}, \d{1,2}:\d{2}(?:\s?[APap][Mm])? - ")

    for line in raw_lines:
        if pattern.match(line):
            if current:
                chat.append(current)
            current = line
        else:
            # Append multi-line message content
            current += "\n" + line
    if current:
        chat.append(current)
    return chat

def parse_chat(chat_text):
    messages = []
    raw_lines = chat_text.splitlines()
    merged_lines = reconstruct_messages(raw_lines)

    # Regex to parse a message line
    pattern = re.compile(r"^(\d{1,2}/\d{1,2}/\d{2,4}), (\d{1,2}:\d{2}(?:\s?[APap][Mm])?) - (.*?): (.*)", re.DOTALL)

    for entry in merged_lines:
        match = pattern.match(entry)
        if match:
            date, time, sender, message = match.groups()

            # Skip messages that are exactly 'null' or system messages without a sender
            if message.strip().lower() == "null" or ":" not in sender:
                continue

            # Try parsing datetime with different formats
            datetime_obj = None
            # Handle AM/PM and 24-hour formats
            time_str = time.replace(' am', ' AM').replace(' pm', ' PM')
            for date_fmt in ['%d/%m/%y, %I:%M %p', '%d/%m/%Y, %I:%M %p', '%d/%m/%y, %H:%M', '%d/%m/%Y, %H:%M']:
                try:
                    datetime_obj = datetime.datetime.strptime(f"{date}, {time_str}", date_fmt)
                    break
                except ValueError:
                    continue
            
            if not datetime_obj:
                continue # Skip if date format is not recognized

            messages.append({
                'datetime': datetime_obj,
                'sender': sender.strip(),
                'message': message.strip()
            })

    # Sort messages by datetime just in case
    messages.sort(key=lambda x: x['datetime'])
    
    # only keep the last 16000 messages
    return messages[-16000:]

def format_messages(messages):
    lines = []
    for msg in messages:
        # Format timestamp back to WhatsApp's original format
        timestamp = msg['datetime'].strftime("%d/%m/%y, %H:%M")
        line = f"{timestamp} - {msg['sender']}: {msg['message']}"
        lines.append(line)
    return "\n".join(lines)


# --- Streamlit UI ---

st.set_page_config(page_title="ChatWrapped", page_icon="📱", layout="wide")
st.title("📱 ChatWrapped: Your WhatsApp Year-in-Review")

# --- Prompts ---
PROMPT_1 = """
tune kar ek AI WhatsApp chat analyst ban gaya hai
tera kaam hai niche diye gaye full chat (.txt file) ka istemal karke ye output dena hai (bina kuch miss kiye)

PART 1:
1. convo ka summary para (masti bhare tone mein likh)
2. dono persons ko funny title de (2-2 line mein justify kar ke)
3. funny inside jokes: 3 heading + subtext + AI comment/quote
4. rage moments: 3 heading + subtext + AI comment/quote
5. emotional sad moments: 3 heading + subtext + AI comment/quote
6. 1 saal pehle is mahine kya interesting chat kiya gaya tha: 1 heading + subtext + AI ki ek line ki tippani
7. most common side characters: 3 names + 2 lines unke baare mein
"""

PROMPT_2 = """
tune pehle hi chat ko analyse kiya hai
ab isi same chat ka istemal karke PART 2 ka  output do:

PART 2:
8. most talked about topics: 3 heading + subtext + AI quote
9. top craziest moments: 2 heading + subtext
10. heartwarming convos: 2 heading + subtext + AI quote
11. Person A ne kya kiya jisse Person B ko sabse zyada khushi mili (heading + subtext + AI comment)
12. Person B ne kya kiya jisse Person A ko sabse zyada khushi mili (heading + subtext + AI comment)
13. Person B ne kya kiya jisse Person A sad hua (heading + subtext + AI comment)
14. Person A ne kya kiya jisse Person B sad hua (heading + subtext + AI comment)
15. Person 1 ka character roast (ek incident ya text based dumb stuff se)
16. Person 2 ka character roast (ek incident ya text based dumb stuff se)
"""

# --- Main App Logic ---

api_key = st.text_input("Enter your Google Gemini API Key", type="password", help="You can get your key from Google AI Studio.")

uploaded_file = st.file_uploader("Upload your exported WhatsApp .txt chat file", type=["txt"])

if uploaded_file and api_key:
    with st.spinner("Processing your chat... This might take a minute!"):
        try:
            # Configure the Gemini client
            genai.configure(api_key=api_key)
            
            # Read and process the chat file
            chat_text = uploaded_file.read().decode("utf-8")
            messages = parse_chat(chat_text)
            
            if not messages:
                st.error("Could not parse any messages from the file. Please ensure it's a valid WhatsApp chat export.")
            else:
                st.success(f"✅ Parsed {len(messages)} messages. Keeping the latest {min(len(messages), 16000)}.")
                stripped_chat_text = format_messages(messages)

                # Setup Gemini model and config
                model = genai.GenerativeModel("gemini-2.0-flash")
                config = {
                    "temperature": 0.7,
                    "response_mime_type": "application/json"
                }

                # --- Generate Part 1 ---
                st.info("Generating Part 1... Almost there!")
                resp1 = model.generate_content(
                    [stripped_chat_text, PROMPT_1],
                    generation_config=config
                )
                part1_json = json.loads(resp1.text)
                
                # --- Generate Part 2 ---
                st.info("Generating Part 2... Finishing up!")
                resp2 = model.generate_content(
                    [stripped_chat_text, PROMPT_2],
                    generation_config=config
                )
                part2_json = json.loads(resp2.text)

                # --- Display Results ---
                st.balloons()
                st.success("Your ChatWrapped is ready!")

                st.subheader("📦 Part 1 Output")
                st.json(part1_json)

                st.subheader("📦 Part 2 Output")
                st.json(part2_json)
                
                # Combine results for download
                final_output = {"part1": part1_json, "part2": part2_json}
                
                st.download_button(
                    "⬇️ Download Full Report (JSON)",
                    data=json.dumps(final_output, indent=4),
                    file_name="chatwrapped_report.json",
                    mime="application/json"
                )

        except Exception as e:
            st.error(f"An error occurred: {e}")
            st.error("Please check your API key and the file format. The model may also be overloaded.")

elif uploaded_file and not api_key:
    st.warning("Please enter your Gemini API key to proceed.")
else:
    st.info("Upload a .txt file and enter your API key to begin.")