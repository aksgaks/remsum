# ✅ main.py (Groq + Whisper + MP3 Upload)

from flask import Flask, request, render_template
import requests, os

app = Flask(__name__)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
WHISPER_API_KEY = os.getenv("WHISPER_API_KEY")  # OpenAI key for transcription

def transcribe_mp3(file):
    headers = {
        "Authorization": f"Bearer {WHISPER_API_KEY}"
    }
    files = {
        'file': (file.filename, file.stream, 'audio/mpeg'),
        'model': (None, 'whisper-1')
    }
    response = requests.post(
        "https://api.openai.com/v1/audio/transcriptions",
        headers=headers,
        files=files
    )
    return response.json().get("text", "")

@app.route("/", methods=["GET", "POST"])
def index():
    summary = ""
    error = ""
    if request.method == "POST":
        note = request.form.get("note", "")
        audio = request.files.get("audio")

        try:
            if audio and audio.filename.endswith(".mp3"):
                note = transcribe_mp3(audio)

            if note:
                response = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {GROQ_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "llama3-8b-8192",
                        "messages": [
                            {"role": "system", "content": "Summarize this note in 2–3 short bullet points suitable as a reminder."},
                            {"role": "user", "content": note}
                        ]
                    }
                )
                data = response.json()
                if "choices" in data:
                    summary = data["choices"][0]["message"]["content"].strip()
                elif "error" in data:
                    error = f"Groq API Error: {data['error'].get('message', 'Unknown error')}"
                else:
                    error = "Unexpected response format."

        except Exception as e:
            error = f"❌ Error: {e}"

    return render_template("index.html", summary=summary, error=error)

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0")
