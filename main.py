from flask import Flask, request, render_template
import requests
import os

app = Flask(__name__)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

@app.route("/", methods=["GET", "POST"])
def index():
    summary = ""
    error = ""
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

                # Check for errors in the response
                if "choices" in data:
                    summary = data["choices"][0]["message"]["content"].strip()
                elif "error" in data:
                    error = f"Groq API Error: {data['error'].get('message', 'Unknown error')}"
                else:
                    error = "Unexpected response format."

            except Exception as e:
                error = f"❌ Exception: {e}"

    return render_template("index.html", summary=summary, error=error)


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0")
