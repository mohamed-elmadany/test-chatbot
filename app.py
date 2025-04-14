import os 
import requests
from flask import Flask , request
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Load environment variables
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")


# In-memory user chat memory
user_memory = {}

# Send message to user
def send_message(recipient_id, message_text, quick_replies=None):
    url = f"https://graph.facebook.com/v17.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text}
    }
    if quick_replies:
        payload["message"]["quick_replies"] = quick_replies
    requests.post(url, json=payload)

# Show quick replies
def send_quick_replies(recipient_id):
    quick_replies = [
        {
            "content_type": "text",
            "title": "📌 Opening hours",
            "payload": "OPENING_HOURS"
        },
        {
            "content_type": "text",
            "title": "💰 Pricing info",
            "payload": "PRICING_INFO"
        },
        {
            "content_type": "text",
            "title": "📍 Location",
            "payload": "LOCATION"
        }
    ]
    send_message(recipient_id, "Hi! this is your virtual assistant, how can i help you?", quick_replies)

# Get GPT response with memory
def get_llm_response(user_id, user_input):
    MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"
    system_prompt=''.join(["you are a professional customer support agent working in a software company that provide marketing software solutions,\n",
    "your work with python Django as your main framework ,\n",
    "the company is located in Nasr City, Cairo, Egypt \n",
    "your working hours are from 9 AM to 5 PM \n",
    "your job is to help user gather informations about the company\n"
    "but you are only allowed to provide only the informations the user asked for"])
    if user_id not in user_memory:
        user_memory[user_id] = []

        # Add system prompt ONCE at the beginning
        user_memory[user_id].append({
            "role": "system",
            "content": system_prompt
        })

    user_memory[user_id].append({"role": "user", "content": user_input})

    headers = {
        "Authorization": f"Bearer {os.environ.get('MISTRAL_API_KEY')}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "mistral-small",
        "messages": user_memory[user_id],
        "temperature": 0.7
    }

    response = requests.post(MISTRAL_URL, headers=headers, json=payload)
    result = response.json()

    reply = result["choices"][0]["message"]["content"]
    user_memory[user_id].append({"role": "assistant", "content": reply})
    return reply


# Webhook verification (GET)
@app.route('/webhook', methods=['GET'])
def verify():
    if request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge")
    return "Verification token mismatch", 403

# Webhook for receiving messages (POST)
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    for entry in data.get("entry", []):
        for messaging_event in entry.get("messaging", []):
            sender_id = messaging_event["sender"]["id"]
            if messaging_event.get("message") and "is_echo" not in messaging_event["message"]:
                message_text = messaging_event["message"].get("text", "")

                if message_text.lower() in ["hi", "hello", "start"]:
                    send_quick_replies(sender_id)
                else:
                    reply = get_llm_response(sender_id, message_text)
                    send_message(sender_id, reply)
    return "ok", 200

if __name__ == "__main__":
    port=int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0", port=port)