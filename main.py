from flask import Flask, request, render_template
import requests
import os

app = Flask(__name__)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

@app.route("/", methods=["GET", "POST"])
def index():
    summary = ""
    if request.method == "POST":
        note = request.form.get("note")
        if note:
            try:
                response = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {GROQ_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "mixtral-8x7b-32768",
                        "messages": [
                            {"role": "system", "content": "Summarize this note in 2–3 short bullet points suitable as a reminder."},
                            {"role": "user", "content": note}
                        ]
                    }
                )
                data = response.json()
                summary = data["choices"][0]["message"]["content"].strip()
            except Exception as e:
                summary = f"❌ Error: {e}"
    return render_template("index.html", summary=summary)

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0")
