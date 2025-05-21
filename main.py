
from flask import Flask, request, render_template
import requests, os, tempfile
import speech_recognition as sr
from pydub import AudioSegment
from vosk import Model

app = Flask(__name__)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Load Vosk model (must be downloaded and placed in a 'model' folder)
vosk_model = Model("model")

def transcribe_vosk(mp3_file):
    recognizer = sr.Recognizer()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as wav_file:
        sound = AudioSegment.from_file(mp3_file, format="mp3")
        sound.export(wav_file.name, format="wav")
        with sr.AudioFile(wav_file.name) as source:
            audio = recognizer.record(source)
            return recognizer.recognize_vosk(audio, model=vosk_model)

@app.route("/", methods=["GET", "POST"])
def index():
    summary = ""
    error = ""
    if request.method == "POST":
        note = request.form.get("note", "")
        audio = request.files.get("audio")

        try:
            if audio and audio.filename.endswith(".mp3"):
                note = transcribe_vosk(audio)

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
            else:
                error = "No valid text or voice input provided."

        except Exception as e:
            error = f"❌ Error: {e}"

    return render_template("index.html", summary=summary, error=error)

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0")
