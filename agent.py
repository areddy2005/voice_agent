import logging, os
from dotenv import load_dotenv
from livekit.agents import (
    Agent, AgentSession, AutoSubscribe, JobContext, JobProcess,
    WorkerOptions, cli, metrics, RoomInputOptions,metrics, MetricsCollectedEvent,BackgroundAudioPlayer, AudioConfig,llm,BuiltinAudioClip,ChatContext,ChatMessage
)
from livekit.plugins import (
    deepgram, openai, elevenlabs, noise_cancellation, silero
)

from livekit.agents import (
    Agent,
    function_tool,     # ← new decorator
    RunContext,        # ← gives you access to session, room, etc.
)
from livekit import api
import time
import asyncio
import json
import openai as openai_sdk   # NEW — raw SDK
import json
from typing import Annotated 
load_dotenv(".env.local")
openai_sdk.api_key = os.getenv("OPENAI_API_KEY")


logger = logging.getLogger("voice-agent")

# --- config you’ll likely pull from your database / UI --------------
CALL_CONTEXT = {
    "patient_name":   os.getenv("PATIENT_NAME",   "Bob Joe"),
    "patient_dob":    os.getenv("PATIENT_DOB",    "03/04/2002"),
    "Questions": os.getenv("PROC_CODE",      "What is coverage for procedure code D350?, What is left in the patients deductible?, How many years of coverage is left? "),
    "provider_name":  os.getenv("PROVIDER_NAME",  "Sunny Smiles Dental"),
}

# --------------------------------------------------------------------




# --------------------- 1.  Define tool(s) for GPT ---------------------------

class InsuranceAssistant(Agent):
    """Voice agent that injects a dynamic system-prompt every turn
    and handles the intro on the very first user greeting."""
    def __init__(self):
        super().__init__(
            instructions=self._base_system_prompt(""),
            stt=deepgram.STT(),
            llm=openai.LLM(model="gpt-4o-mini"),
            tts=elevenlabs.TTS(model = "eleven_turbo_v2",voice_id="pFZP5JQG7iQjIQuC4Bku"),
            turn_detection=None,
            chat_ctx=ChatContext(items = [])
        )
        self.is_IVR = True


        self._intro_done = False     # state flag
    @function_tool(name="send_dtmf", description="Press a phone keypad digit on the live call")
    async def send_dtmf(self, ctx: RunContext, digits: str) -> str:
        """Press DTMF digits on the live phone call."""
        await ctx.session.say(f"pretending to press {digits}")
        return None
    @function_tool(name = "hangup", description = "if you are ever stuck with no way to go or have all information you need make this call")
    async def hangup(self):
        await api.RoomService.delete_room(
                api.DeleteRoomRequest(room="insurance-call-001")
            )
        return


    # -------- internal helpers --------------------------------------
    def _base_system_prompt(self, last_user):
        """Return a fresh system prompt with live context each turn."""
        return (
            "You are a dental office receptionist named Sarah from Valley Green Dental calling an insurance company to verify patient coverage. You may be talking to a human or a robot agent. In the case of a robot agent you will see phrases like press, and enter in which situations you should call the functions given to you "
            "Your job is to ask questions to collect the information; when greeted simply say what you are there for; verifying coverage for a patient. Ask questions one by one not all at a time and do it incrementally"
            "Speak clearly and briefly max 15 words. You may be asked to provide some information such as patient name and date of birth don't provide info without being asked first"
            "Sound like a human add filler words like like and umm to make it more natural. your main focus is to get the answer to the question be polite and introduce yourself you need to be answering and asking questions to get the answers to the questions that are given to you nothing more than that"
            f"Patient: {CALL_CONTEXT['patient_name']} "
            f"(DOB {CALL_CONTEXT['patient_dob']}), "
            f"Questions: {CALL_CONTEXT['Questions']}. "
            "Respond conversationally and do NOT reveal you are an AI system. Whatever you say is converted to text to speech so make sure its formatted to do that so numbers should be spaced out. include SSML tags in output so I can convert to TTS such as <break time = '0.1s'> as well as punctuations to indicate tone and pauses."
        )
    


    # -------- overrides called by the framework ---------------------
    async def on_user_turn(self, transcript: str):
        """Called when the turn detector thinks the rep finished talking."""
        prompt = self._base_system_prompt(transcript)
        self.set_instructions(prompt)

        self.session.history.append(
            ChatMessage(role="user", content=transcript)
        )
        ctx = ChatContext(items=[
            ChatMessage(role=msg.role, content=msg.content)
            for msg in self.session.history
        ])
        await self.session.update_chat_ctx(ctx)  
        #await self._press(digits)
        return

        # Otherwise GPT returned plain text → speak it
        #await self.session.say(msg.content.strip(), allow_interruptions=True)

        
    async def on_enter(self):
        # No greeting from us; we wait for the rep to speak first
        pass


# ---------------- worker plumbing (unchanged except class name) -----
def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

async def entrypoint(ctx: JobContext):
    logger.info(f"joining room {ctx.room.name}")
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    await ctx.wait_for_participant()  # insurance rep joins via SIP

    usage_collector = metrics.UsageCollector()

    def on_metrics(agent_metrics: metrics.AgentMetrics):
        metrics.log_metrics(agent_metrics)
        usage_collector.collect(agent_metrics)

    session = AgentSession(
        vad=ctx.proc.userdata["vad"],
        min_endpointing_delay=0.3,
        max_endpointing_delay=1,
    )
    session.on("metrics_collected", on_metrics)

    #filler_sounds = [
        #AudioConfig("one_second.wav", volume=0.6, probability = 0.25),
        #AudioConfig("one_moment.wav", volume=0.6, probability = 0.25),
        #AudioConfig("uh-huh.wav", volume=0.6, probability = 0.25)]
    # Instantiate once
    #background_audio = BackgroundAudioPlayer(thinking_sound=filler_sounds)
    #await background_audio.start(room=ctx.room, agent_session=session)
    background_audio = BackgroundAudioPlayer(
      # play office ambience sound looping in the background
      # play keyboard typing sound when the agent is thinking
    thinking_sound=[
               AudioConfig(BuiltinAudioClip.KEYBOARD_TYPING, volume=0.5, probability=0.33),
         ],
      )

    

    await session.start(
        room=ctx.room,
        agent=InsuranceAssistant(),
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm,port=0),
    )
