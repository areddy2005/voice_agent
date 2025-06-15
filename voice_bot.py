
import os, requests, base64, hashlib
from flask import Flask, request, Response, send_file
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Gather
from urllib.parse import quote
import openai

app = Flask(__name__)
CALL_CONTEXT = {}
# ── CONFIG ─────────────────────────────────────────────────────────────────────
TWILIO_SID   = "ACf0310d612d324f85cbe4eee2d83caaea"
TWILIO_TOKEN = "7b28e5855bedee068d9adce5361abdf9"
TWILIO_NUM   = "+18776783869"   # your Twilio number
PAYER_NUM    = "+19255492810"   # e.g. "+18005551234"
client       = Client(TWILIO_SID, TWILIO_TOKEN)
openai.api_key = "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"
GOOGLE_API_KEY= "AIzaSyCMsTwEm_edJVSz9G7jJ_yjyUrKQVEZqbA"
TTS_URL = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={GOOGLE_API_KEY}"
LOCAL_URL = "https://good-teeth-chew.loca.lt"
# ── ENDPOINTS ──────────────────────────────────────────────────────────────────
FIELDS = [
    "annual maximum benefit",
    "used-to-date amount",
    "individual deductible",
    "deductible met so far",
    "preauthorization requirements",
    "coverage type"
]
def synthesize_wav(text: str) -> str:
    # Hash to cache identical texts
    fn   = hashlib.sha1(text.encode()).hexdigest() + ".wav"
    path = os.path.join("/tmp", fn)
    if not os.path.exists(path):
        payload = {
            "input": {"text": text},
            "voice": {
                "languageCode": "en-US",
                "name": "en-US-Wavenet-D",
                "ssmlGender": "MALE"
            },
            "audioConfig": {
                "audioEncoding": "LINEAR16",
                "sampleRateHertz": 24000
            }
        }
        r = requests.post(TTS_URL, json=payload)
        r.raise_for_status()
        audio = r.json()["audioContent"]
        with open(path, "wb") as f:
            f.write(base64.b64decode(audio))
    return path

@app.route("/tts", methods=["GET"])
def tts_endpoint():
    text = request.args.get("text","")
    if not text:
        return "Missing text", 400
    wav = synthesize_wav(text)
    return send_file(wav, mimetype="audio/wav")

@app.route("/wait_for_voice", methods=["POST"])
def wait_for_voice():
    """
    Wait up to 30 minutes for the rep to speak.
    As soon as any speech is detected, Twilio will POST to /gather.
    If no speech is heard in 30 minutes, we hang up.
    """
    vr = VoiceResponse()
    # Gather speech only — no <Say> — listen up to 1800 s
    g = Gather(
        input="speech",
        action="/gather",     # your next handler
        method="POST",
        timeout=1800,         # wait up to 30 minutes for first speech
        speech_timeout="auto" # once speech starts, end when they pause
    )
    vr.append(g)
    # If they never speak, hang up after timeout
    vr.say("No response detected. Goodbye.", voice="Polly.Joanna")
    vr.hangup()
    return Response(str(vr), mimetype="text/xml")

@app.route("/place_call", methods=["POST"])
def place_call():
    """Trigger the outbound call to your payer."""
    call = client.calls.create(
        to=PAYER_NUM,
        from_=TWILIO_NUM,
        url= "https://good-teeth-chew.loca.lt/" + "wait_for_voice"   # Twilio will fetch this once connected
    )
    CALL_CONTEXT[call.sid] = [
        {"role": "system", "content": 
        "You are a receptionist and are calling an insurance company to get information about the money left in a patient's deductible and if the procedure D350 is covered"
        "act like a human the insurance agent can not know you are a AI You may be asked for information to confirm the patients Identity. His name is Arjun Reddy and the last 4 digits of his SSN are 3304"
        "Keep Responses Short"
        }]
    return {"call_sid": call.sid}, 201

@app.route("/gather", methods=["POST"])
def gather():
    call_sid = request.values["CallSid"]
    context  = CALL_CONTEXT[call_sid]

    # 1) Capture rep’s latest turn
    rep_text = request.values.get("SpeechResult","").strip()
    context.append({"role": "user", "content": rep_text})

    # 2) Ask GPT for your next line (it sees entire history)
    resp = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=context,
        temperature=0.7,
        max_tokens=7
    )
    bot_line = resp.choices[0].message.content.strip()
    # 3) Append your turn so it’ll be in context next time
    context.append({"role": "assistant", "content": bot_line})

    # 4) Build TwiML to say & gather again
    wav_url = f"{LOCAL_URL}/tts?text={quote(bot_line)}"
    vr = VoiceResponse()
    g  = Gather(
        input="speech",
        action="/gather",
        speech_timeout="auto",
        barge_in=True
    )

    #g.say(bot_line, voice="Polly.Joanna")
    g.play(wav_url)
    vr.append(g)
    vr.redirect("/gather")
    return Response(str(vr), mimetype="text/xml")

@app.route("/ask", methods=["POST"])
def ask():
    """Ask one question and gather their spoken reply."""
    vr = VoiceResponse()
    g  = Gather(
        input="speech",         # use Twilio’s STT
        action="/transcribe",   # callback to handle the transcript
        speech_timeout="auto"
    )
    g.say("Hello. Please say the patient’s full name after the tone.")
    vr.append(g)
    # if no speech detected, retry once
    vr.redirect("/ask")
    return Response(str(vr), mimetype="text/xml")

@app.route("/transcribe", methods=["POST"])
def transcribe():
    """Log what Twilio captured as speech."""
    transcript = request.values.get("SpeechResult", "")
    print("🔊 Transcribed:", transcript)
    # You can store it in a database or return it in the response
    vr = VoiceResponse()
    vr.say("Thank you. Goodbye.")
    vr.hangup()
    return Response(str(vr), mimetype="text/xml")

if __name__ == "__main__":
    app.run(port=5000)