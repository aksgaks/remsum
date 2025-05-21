
from flask import Flask, request, render_template
import requests, os, tempfile, zipfile, wave, json
from pydub import AudioSegment
from vosk import Model, KaldiRecognizer

# ✅ Auto-download Vosk model if not already present
def setup_vosk_model():
    model_url = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
    model_zip_path = "model.zip"
    model_dir = "model"

    if not os.path.exists(model_dir):
        print("🔽 Downloading Vosk model...")
        response = requests.get(model_url, stream=True)
        with open(model_zip_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        print("📦 Unzipping model...")
        with zipfile.ZipFile(model_zip_path, "r") as zip_ref:
            zip_ref.extractall(".")
            extracted_folder = zip_ref.namelist()[0].split("/")[0]
            os.rename(extracted_folder, model_dir)

        os.remove(model_zip_path)
        print("✅ Vosk model ready.")

# Run model setup
setup_vosk_model()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Load Vosk model
vosk_model = Model("model")

def transcribe_vosk(audio_file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as wav_file:
        sound = AudioSegment.from_file(audio_file)
        sound.export(wav_file.name, format="wav")

    wf = wave.open(wav_file.name, "rb")
    rec = KaldiRecognizer(vosk_model, wf.getframerate())

    transcript = ""
    while True:
        data = wf.readframes(4000)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            result = json.loads(rec.Result())
            transcript += result.get("text", "") + " "

    final_result = json.loads(rec.FinalResult())
    transcript += final_result.get("text", "")
    return transcript.strip()

@app.route("/", methods=["GET", "POST"])
def index():
    summary = ""
    error = ""
    if request.method == "POST":
        note = request.form.get("note", "")
        audio = request.files.get("audio")

        try:
            if audio and audio.filename.lower().endswith((".mp3", ".m4a", ".wav", ".ogg")):
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
