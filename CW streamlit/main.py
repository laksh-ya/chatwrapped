import streamlit as st
import re
import nltk

import datetime
from collections import defaultdict, Counter
import matplotlib.pyplot as plt
from wordcloud import WordCloud
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import emoji

nltk.download('punkt')
nltk.download('stopwords')
nltk.data.path.append('./nltk_data')

# 🌪 Clean chat: removes media, counts deleted msgs
def clean_chat(raw_lines):
	media_count = 0
	deleted_msgs = defaultdict(int)
	cleaned_lines = []
	# match both 12hr and 24hr formats
	pattern = re.compile(r"^\d{1,2}/\d{1,2}/\d{2,4}, \d{1,2}:\d{2}(?:\s?[APap][Mm])? - (.*?): (.*)$")

	for line in raw_lines:
		if "<Media omitted>" in line:
			media_count += 1
			continue
		if re.search(r": null$", line.strip()):
			continue
		match = pattern.match(line.strip())
		if match:
			sender, message = match.groups()
			if message.strip().lower() in ["you deleted this message", "this message was deleted"]:
				deleted_msgs[sender] += 1
				continue
		cleaned_lines.append(line)
	return cleaned_lines, media_count, deleted_msgs

# 🧠 Parse each message
def parse_chat(chat_text):
	messages = []
	# handle both 24hr and 12hr with am/pm
	pattern = re.compile(r"^(\d{1,2}/\d{1,2}/\d{2,4}), (\d{1,2}:\d{2}(?:\s?[APap][Mm])?) - (.*?): (.*)$")
	lines = chat_text.splitlines()
	for line in lines:
		match = pattern.match(line)
		if match:
			date, time, sender, message = match.groups()
			# try both date formats
			for date_fmt in ['%d/%m/%y %I:%M %p', '%d/%m/%Y %I:%M %p', '%d/%m/%y %H:%M', '%d/%m/%Y %H:%M']:
				try:
					datetime_obj = datetime.datetime.strptime(f"{date} {time}", date_fmt)
					break
				except:
					continue
			else:
				continue  # skip if date parsing fails
			messages.append({
				'datetime': datetime_obj,
				'sender': sender.strip(),
				'message': message.strip()
			})
	return messages

# 🔢 Basic stats
def get_total_messages(messages):
	return len(messages)

def get_messages_by_sender(messages):
	counts = defaultdict(int)
	for msg in messages:
		counts[msg['sender']] += 1
	return dict(counts)

def get_most_active_hour(messages):
	hour_counts = [0]*24
	for msg in messages:
		hour_counts[msg['datetime'].hour] += 1
	return hour_counts.index(max(hour_counts))

def detect_convo_starters(messages, gap_minutes=240):
	starters = defaultdict(int)
	prev_time = messages[0]['datetime']
	for msg in messages[1:]:
		gap = (msg['datetime'] - prev_time).total_seconds() / 60.0
		if gap >= gap_minutes:
			starters[msg['sender']] += 1
		prev_time = msg['datetime']
	return dict(starters)

def get_longest_reply_gap(messages):
	max_gap = datetime.timedelta()
	gap_msg = ('', '')
	for i in range(1, len(messages)):
		gap = messages[i]['datetime'] - messages[i-1]['datetime']
		if gap > max_gap:
			max_gap = gap
			gap_msg = (messages[i-1]['message'], messages[i]['message'])
	return max_gap, gap_msg

def get_monthly_message_counts(messages):
	month_counts = defaultdict(int)
	for msg in messages:
		month = msg['datetime'].strftime('%b %Y')
		month_counts[month] += 1
	return dict(month_counts)

def get_top_words(messages, top_n=100):
	all_text = ' '.join(msg['message'] for msg in messages if msg['message'] != 'null')
	words = word_tokenize(all_text.lower())
	stop_words = set(stopwords.words('hinglish') + stopwords.words('english'))
	filtered = [w for w in words if w.isalnum() and w not in stop_words]
	word_freq = Counter(filtered)
	return word_freq.most_common(top_n)

def get_emoji_stats(messages, top_n=10):
	total_emojis = 0
	emoji_counter = Counter()
	emoji_by_user = defaultdict(int)

	for msg in messages:
		text = msg['message']
		emojis = [ch for ch in text if ch in emoji.EMOJI_DATA]
		total_emojis += len(emojis)
		emoji_counter.update(emojis)
		emoji_by_user[msg['sender']] += len(emojis)

	top_emojis = emoji_counter.most_common(top_n)
	most_emoji_sender = max(emoji_by_user.items(), key=lambda x: x[1], default=("None", 0))

	return total_emojis, top_emojis, most_emoji_sender

# 🧠 UI STARTS HERE
st.title("🧠 WhatsApp Chat Analyzer")

uploaded_file = st.file_uploader("Upload your WhatsApp chat (.txt file)", type="txt")

if uploaded_file is not None:
	raw_lines = uploaded_file.read().decode("utf-8").splitlines()
	cleaned_lines, media_count, deleted_msgs = clean_chat(raw_lines)
	chat_text = "\n".join(cleaned_lines)
	messages = parse_chat(chat_text)

	st.subheader("📊 Basic Stats")
	st.write("Total Messages:", get_total_messages(messages))
	st.write("Messages by Sender:", get_messages_by_sender(messages))
	st.write("Media Messages Removed:", media_count)
	for sender, count in deleted_msgs.items():
		st.write(f"Deleted messages by {sender}: {count}")

	st.subheader("🕒 Most Active Hour")
	st.write(get_most_active_hour(messages))

	st.subheader("🧠 Conversation Starters")
	st.write(detect_convo_starters(messages))

	st.subheader("⌛ Longest Reply Gap")
	max_gap, (msg1, msg2) = get_longest_reply_gap(messages)
	st.write(f"Gap: {max_gap}")
	st.write("Before:", msg1)
	st.write("After:", msg2)

	st.subheader("📅 Messages Per Month")
	monthly_data = get_monthly_message_counts(messages)
	st.bar_chart(monthly_data)

	st.subheader("🧠 Top Words")
	top_words = get_top_words(messages)
	st.write(top_words)

	st.subheader("☁️ Word Cloud")
	wc = WordCloud(width=800, height=400, background_color='white').generate_from_frequencies(dict(top_words))
	st.image(wc.to_array())

	st.subheader("😂 Emoji Stats")
	total_emojis, top_emojis, most_emoji_sender = get_emoji_stats(messages)
	st.write(f"Total Emojis Sent: {total_emojis}")
	st.write("Top Emojis:", top_emojis)
	st.write(f"Most Emoji Sender: {most_emoji_sender[0]} ({most_emoji_sender[1]} emojis)")

	st.subheader("☁️ Emoji Cloud")
	emoji_text = ''.join([emoji * count for emoji, count in top_emojis])
	if emoji_text.strip():
		emoji_cloud = WordCloud(width=800, height=400, background_color='white', font_path=None, regexp=r"[^\s]").generate(emoji_text)
		st.image(emoji_cloud.to_array())
	else:
		st.warning("No emojis found to generate the emoji cloud 🥲")