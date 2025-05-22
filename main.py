
from flask import Flask, request, render_template
import os, tempfile, wave, json, datetime
from pydub import AudioSegment
from vosk import Model, KaldiRecognizer
import requests, smtplib
from email.mime.text import MIMEText
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Auto-download Vosk model
def setup_vosk_model():
    model_url = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
    model_zip_path = "model.zip"
    model_dir = "model"
    if not os.path.exists(model_dir):
        print("Downloading Vosk model...")
        response = requests.get(model_url, stream=True)
        with open(model_zip_path, "wb") as f:
            for chunk in response.iter_content(8192):
                f.write(chunk)
        import zipfile
        with zipfile.ZipFile(model_zip_path, "r") as zip_ref:
            zip_ref.extractall(".")
            extracted_folder = zip_ref.namelist()[0].split("/")[0]
            os.rename(extracted_folder, model_dir)
        os.remove(model_zip_path)

setup_vosk_model()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

vosk_model = Model("model")

def transcribe_vosk(audio_file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as wav_file:
        sound = AudioSegment.from_file(audio_file)
        sound = sound.set_frame_rate(16000).set_channels(1)
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

def send_email(to_email, content):
    msg = MIMEText(content)
    msg["Subject"] = "Your Reminder Summary"
    msg["From"] = EMAIL_USER
    msg["To"] = to_email
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)

def create_calendar_event(summary, dt):
    creds_dict = json.loads(os.environ["GOOGLE_CREDENTIALS"])
    credentials = service_account.Credentials.from_service_account_info(
        creds_dict, scopes=["https://www.googleapis.com/auth/calendar"]
    )
    service = build("calendar", "v3", credentials=credentials)
    event = {
        'summary': 'Reminder',
        'description': summary,
        'start': {'dateTime': dt.isoformat(), 'timeZone': 'Asia/Kolkata'},
        'end': {'dateTime': (dt + datetime.timedelta(hours=1)).isoformat(), 'timeZone': 'Asia/Kolkata'},
    }
    service.events().insert(calendarId='primary', body=event).execute()

@app.route("/", methods=["GET", "POST"])
def index():
    summary = ""
    error = ""
    transcript = ""
    if request.method == "POST":
        note = request.form.get("note", "")
        audio = request.files.get("audio")
        user_email = request.form.get("email")
        send_email_flag = request.form.get("send_email")
        reminder_time = request.form.get("reminder_datetime")
        summarize_flag = request.form.get("summarize")

        try:
            if audio and audio.filename.lower().endswith((".mp3", ".m4a", ".wav", ".ogg", ".mp4")):
                transcript = transcribe_vosk(audio)
                note = transcript

            if note:
                if summarize_flag:
                    res = requests.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                        json={
                            "model": "llama3-8b-8192",
                            "messages": [
                                {"role": "system", "content": "Summarize this note in 2–3 short bullet points suitable as a reminder."},
                                {"role": "user", "content": note}
                            ]
                        }
                    )
                    data = res.json()
                    summary = data["choices"][0]["message"]["content"].strip()
                else:
                    summary = note

                if send_email_flag and user_email:
                    send_email(user_email, summary)

                if reminder_time:
                    reminder_dt = datetime.datetime.fromisoformat(reminder_time)
                    create_calendar_event(summary, reminder_dt)

            else:
                error = "No input provided."

        except Exception as e:
            error = f"Error: {e}"

    return render_template("index.html", summary=summary, error=error, transcript=transcript)

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0")
