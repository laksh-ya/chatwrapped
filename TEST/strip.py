import streamlit as st
import re
import datetime

st.title("📥 WhatsApp Chat Processor")

uploaded_file = st.file_uploader("Upload WhatsApp chat (.txt)", type="txt")

# helper to merge multi-line messages properly
def reconstruct_messages(raw_lines):
	chat = []
	current = ""
	pattern = re.compile(r"^\d{1,2}/\d{1,2}/\d{2,4}, \d{1,2}:\d{2}(?:\s?[APap][Mm])? - ")

	for line in raw_lines:
		if pattern.match(line):
			if current:
				chat.append(current)
			current = line
		else:
			current += "\n" + line
	if current:
		chat.append(current)
	return chat

def parse_chat(chat_text):
	messages = []
	raw_lines = chat_text.splitlines()
	merged_lines = reconstruct_messages(raw_lines)

	pattern = re.compile(r"^(\d{1,2}/\d{1,2}/\d{2,4}), (\d{1,2}:\d{2}(?:\s?[APap][Mm])?) - (.*?): (.*)", re.DOTALL)

	for entry in merged_lines:
		match = pattern.match(entry)
		if match:
			date, time, sender, message = match.groups()

			# skip messages that are exactly 'null'
			if message.strip().lower() == "null":
				continue

			for date_fmt in ['%d/%m/%y %I:%M %p', '%d/%m/%Y %I:%M %p', '%d/%m/%y %H:%M', '%d/%m/%Y %H:%M']:
				try:
					datetime_obj = datetime.datetime.strptime(f"{date} {time}", date_fmt)
					break
				except:
					continue
			else:
				continue

			messages.append({
				'datetime': datetime_obj,
				'sender': sender.strip(),
				'message': message.strip()
			})

	# only keep the last 26000 messages
	return messages[-16000:]

def format_messages(messages):
	lines = []
	for msg in messages:
		timestamp = msg['datetime'].strftime("%d/%m/%Y, %H:%M")
		line = f"{timestamp} - {msg['sender']}: {msg['message']}"
		lines.append(line)
	return "\n".join(lines)

if uploaded_file is not None:
	chat_text = uploaded_file.read().decode("utf-8")
	messages = parse_chat(chat_text)

	st.success(f"✅ Parsed {len(messages)} messages (latest 26000, multi-line safe, 'null' removed).")

	if st.checkbox("Show sample messages"):
		for msg in messages[:5]:
			st.markdown(f"**{msg['sender']}** at *{msg['datetime']}*: {msg['message']}")

	formatted_text = format_messages(messages)
	st.download_button("📄 Download Processed Chat", formatted_text, file_name="processed_chat.txt", mime="text/plain")