
import os, requests, base64, hashlib
from flask import Flask, request, Response, send_file
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Gather
from urllib.parse import quote
import openai
import random
import threading, time
import httpx, openai

FILLER_TEXTS = [
    "<speak>O-kay<break time='500ms'/></speak>",
    "<speak>Let me see here …<break time='400ms'/></speak>",
]
FILLER_WAV   = {}  # text ➜ local file path


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
LOCAL_URL = "https://happy-moles-slide.loca.lt"
# ── ENDPOINTS ──────────────────────────────────────────────────────────────────
httpx_client = httpx.Client(timeout=20.0)                  # ← keeps TLS open
gpt_client  = openai.OpenAI(                           # new v1 client
    api_key=openai.api_key,
    http_client=httpx_client
)
FIELDS = [
    "annual maximum benefit",
    "used-to-date amount",
    "individual deductible",
    "deductible met so far",
    "preauthorization requirements",
    "coverage type"
]
"""
def random_filler_url() -> str:
    filler = random.choice(FILLER_TEXTS)
    return f"{LOCAL_URL}/tts?text={quote(filler)}"
def synthesize_wav(text: str) -> str:
    # Hash to cache identical texts
    fn   = hashlib.sha1(text.encode()).hexdigest() + ".mp3"
    path = os.path.join("/tmp", fn)
    is_ssml = text.lstrip().startswith("<speak>")
    if not os.path.exists(path):
        payload = {
            "input": {"ssml" if is_ssml else "text": text},
            "voice": {
                "languageCode": "en-US",
                "name":  "en-US-Studio-M",
                "ssmlGender": "MALE"
            },
            "audioConfig": {
                "audioEncoding": "MP3",
                "sampleRateHertz": 24000,
                 "speakingRate": 1.35 
            }
        }
        r = requests.post(TTS_URL, json=payload)
        r.raise_for_status()
        audio = r.json()["audioContent"]
        with open(path, "wb") as f:
            f.write(base64.b64decode(audio))
    return path
# pre–synthesise once
for t in FILLER_TEXTS:
    FILLER_WAV[t] = synthesize_wav(t)
@app.route("/tts", methods=["GET"])
def tts_endpoint():
    text = request.args.get("text","")
    if not text:
        return "Missing text", 400
    wav = synthesize_wav(text)
    return send_file(wav, mimetype="audio/mpeg")

@app.route("/wait_for_voice", methods=["POST"])
def wait_for_voice():
    
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
    """"""
    call = client.calls.create(
        to=PAYER_NUM,
        from_=TWILIO_NUM,
        url= "https://grumpy-chicken-cheat.loca.lt/" + "wait_for_voice"   # Twilio will fetch this once connected
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
    ctx      = CALL_CONTEXT.get(call_sid, [])
    user_tx  = request.values.get("SpeechResult", "").strip()

    # spawn GPT in background
    threading.Thread(target=compute_reply_async,
                     args=(call_sid, ctx, user_tx),
                     daemon=True).start()

    filler_ssml = random.choice(FILLER_TEXTS)
    filler_url  = f"{LOCAL_URL}/tts?text={quote(filler_ssml)}"
    vr = VoiceResponse()
    vr.play(filler_url)                 # play immediately
    vr.redirect("/answer")              # Twilio calls back next
    return Response(str(vr), mimetype="text/xml")

@app.route("/answer", methods=["POST"])
def answer():
    call_sid = request.values["CallSid"]
    reply    = CALL_CONTEXT.get(call_sid + "_reply")

    # if GPT still thinking, pause 1 s and try again
    if reply is None:
        vr = VoiceResponse()
        vr.pause(length=1)
        vr.redirect("/answer")
        return Response(str(vr), mimetype="text/xml")

    # GPT is ready – speak it inside a barge-in gather
    wav_url = f"{LOCAL_URL}/tts?text={quote(reply)}"
    vr  = VoiceResponse()
    g   = Gather(input="speech", action="/gather",
                 method="POST", timeout=8,
                 speech_timeout="auto", barge_in=True)
    g.play(wav_url)
    vr.append(g)
    vr.redirect("/gather")
    return Response(str(vr), mimetype="text/xml")


def compute_reply_async(call_sid, ctx, user_text):
    """"""
    ctx.append({"role": "user", "content": user_text})
    resp = gpt_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=ctx,
        temperature=0.7,
        max_tokens=25
    )
    answer = resp.choices[0].message.content.strip()
    ctx.append({"role": "assistant", "content": answer})
    CALL_CONTEXT[call_sid + "_reply"] = answer     # cache for /answer

@app.route("/ask", methods=["POST"])
def ask():
    """"""
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
    """"""
    transcript = request.values.get("SpeechResult", "")
    print("🔊 Transcribed:", transcript)
    # You can store it in a database or return it in the response
    vr = VoiceResponse()
    vr.say("Thank you. Goodbye.")
    vr.hangup()
    return Response(str(vr), mimetype="text/xml")
"""
# ── 1. OUTBOUND CALL → WAIT FOR VOICE ────────────────────────────────
@app.route("/place_call", methods=["POST"])
def place_call():
    call = client.calls.create(
        to   = PAYER_NUM,
        from_= TWILIO_NUM,
        url  = LOCAL_URL+"/" + "wait_for_voice"
    )
    # seed the chat history
    CTX[call.sid] = [{
        "role": "system",
        "content": (
            "You are a friendly receptionist calling an insurance rep. "
            "Keep your replies concise and conversational."
        )
    }]
    return {"call_sid": call.sid}, 201

@app.route("/wait_for_voice", methods=["POST"])
def wait_for_voice():
    """Wait up to 30m for the rep to start speaking, then hand off to /loop."""
    vr = VoiceResponse()
    vr.gather(
        input          = "speech",
        action         = "/loop",
        method         = "POST",
        timeout        = 1800,      # 30 minutes
        speech_timeout = "auto"     # end on pause
    )
    vr.say("No response detected. Goodbye.", voice="Polly.Joanna")
    vr.hangup()
    return Response(str(vr), mimetype="text/xml")


# ── 2. MAIN LOOP: GATHER → GPT → SAY → GATHER ─────────────────────────
@app.route("/loop", methods=["POST"])
def loop():
    call_sid = request.values["CallSid"]
    user_txt = request.values.get("SpeechResult", "").strip()
    history  = CALL_CONTEXT.setdefault(call_sid, [])

    # record what the rep said (skip first empty fetch)
    if user_txt:
        history.append({"role": "user", "content": user_txt})

    # call GPT synchronously and time it
    t0   = time.perf_counter()
    resp = gpt_client.chat.completions.create(
        model       = "gpt-3.5-turbo",
        messages    = history,
        temperature = 0.6,
        max_tokens  = 30,
    )
    reply = resp.choices[0].message.content.strip()
    dt    = (time.perf_counter() - t0) * 1000
    print(f"[GPT latency] {dt:.0f} ms → {reply[:60]}…")

    # save into history
    history.append({"role": "assistant", "content": reply})

    # speak the reply and then gather again
    vr = VoiceResponse()
    g  = Gather(
        input          = "speech",
        action         = "/loop",
        method         = "POST",
        timeout        = 8,
        speech_timeout = "auto",
        barge_in       = True
    )
    g.say(reply, voice="Polly.Joanna")
    vr.append(g)
    return Response(str(vr), mimetype="text/xml")


if __name__ == "__main__":
    app.run(port=5000)