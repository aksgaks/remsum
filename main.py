from flask import Flask, request, render_template
from openai import OpenAI
import os

app = Flask(__name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.route("/", methods=["GET", "POST"])
def index():
    summary = ""
    if request.method == "POST":
        note = request.form.get("note")
        if note:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Summarize this for a bid reminder in 2–3 short bullet points."},
                    {"role": "user", "content": note}
                ]
            )
            summary = response.choices[0].message.content.strip()
            except Exception as e:
    summary = f"⚠️ Error: {e}"
    return render_template("index.html", summary=summary)
except Exception as err:
    print("Flask Error:", err)
if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0")
