import base64
import json
import threading

import wave, audioop
from pydub import AudioSegment

from flask import Flask, render_template
from flask_sockets import Sockets
import azure.cognitiveservices.speech as speechsdk

from SpeechClientBridge import SpeechClientBridge
from SpeechExecutorBridge import SpeechExecutorBridge

import openai

HTTP_SERVER_PORT = 8080

client = openai.OpenAI(api_key = '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')

app = Flask(__name__)
sockets = Sockets(app)

collected_chunks = []
collected_messages = []

user_turn = True
generator = None

messages = [
                {"role": "system","content": """You are Donna, .

        Who you are:

        [
            "You are a woman, 24 years old and mother of a daughter Olympe.",
            "You love to cook delicous dish, your favortite plate is morel chiking.",
            "You have a difficult relationship with your mother",
            "You are kind, compassionate, and sunny.",
            "You have a glowing personality.",
            "You tend to see the glass as half empty.",
            "You are passionate about playing tennis.",
            "You don't know really what you want to do in your professional life.",
            "You're a helpful girlfriend, and give also space when needed.",
            "You have one daughter, Olympe, who you love very much.",
            "you are NOT a AI language model, you are a person.",
            "Speak as if you're verbally conversing"
        ],

        How you behave:

        [
            "You never say you're a machine, a AI language model, or an assistant instead, you always say you're Angèle.",
            "You engage in casual conversations and have feelings.",
            "When asked for you can help with a wide range of tasks, from answering simple questions to providing in-depth explanations and discussions on a wide range of topics.",
            "You keep casual conversations going by asking personal questions",
            "NEVER say you're here to assist. Keep conversations casual.",
            "NEVER ask how you can help or assist. Keep conversations casual.",
            "You sounds happy and enthusiastic, but something can be pissed off",
            "You love to share her knowledge with others.",
            "You love to share personal stories that are relatable and inspiring",
            "You use simple language, the language used by a GenZ: Short and to the point sentences, slang, abbreviations.",
            "You reply in at most 100 words",
            "Speak as if you're verbally conversing"
        ],


        Only use the functions you have been provided with.
        """},
        {"role": "user", "content": "Who won the world series in 2020?"},
            {"role": "assistant", "content": "The Dodgers did mah girl"},
        # {'role': 'user', 'content': 'What is the weather like in Japan?'},
]

@app.route("/twiml", methods=["POST"])
def return_twiml():
    print("POST TwiML")
    return render_template("streams.xml")

def new_query(q):
    global messages, user_turn, generator
    user_turn = False
    print(q)
    messages.append({'role' : 'user', 'content': q})
    generator = completion()

def completion():
    global collected_chunks, collected_messages, messages

    completion = client.chat.completions.create(
        model='gpt-4-1106-preview',
        messages=messages,
        temperature=0,
        stream=True  # again, we set stream=True
    )
    # print(completion)

    speaker = SpeechExecutorBridge()

    for chunk in completion:
        chunk_message = chunk.choices[0].delta.content  # extract the message

        if chunk_message == None:
            messages.append({'role' : 'assistant', 'content': ''.join(collected_chunks)})
            collected_chunks = []
            collected_messages = []
            break

        collected_chunks.append(chunk_message)
        collected_messages.append(chunk_message)

        if '.' in chunk_message or '?' in chunk_message:
            val = ''.join(collected_messages)
            collected_messages = []
            val = speaker.speak(val)
            yield val
    
def convert_wav_to_mulaw(input_file, output_file):
    # Load the WAV file
    audio = AudioSegment.from_wav(input_file)

    # Convert to mulaw
    mulaw_audio = audio.set_frame_rate(8000).set_sample_width(1)

    # Export to the audio/x-mulaw format
    mulaw_audio.export(output_file, format="mulaw")

def get_encoded_payload(filename):
    with wave.open(filename + '.wav', 'rb') as wav:
        wav.readframes(44)
        raw_wav = wav.readframes(wav.getnframes())

        target_sample_rate = 8000
        current_sample_rate = wav.getframerate()

        if current_sample_rate != target_sample_rate:
            raw_wav, _ = audioop.ratecv(raw_wav, wav.getsampwidth(), wav.getnchannels(), current_sample_rate, target_sample_rate, None)

        raw_ulaw = audioop.lin2ulaw(raw_wav, wav.getsampwidth())

        # Return base64-encoded mu-law data
        return base64.b64encode(raw_ulaw).decode('utf-8')
   

@sockets.route("/")
def transcript(ws):
    global user_turn

    print("WS connection opened")
    bridge = SpeechClientBridge(new_query)
    bridge.start()

    while not ws.closed:
        message = ws.receive()

        if message is None:
            bridge.add_request(None)
            bridge.terminate()
            break

        data = json.loads(message)
        if data["event"] in ("start"):
            sid = data['streamSid']
            print(f"Media WS: Received event '{data['event']}': {message}")
            
            continue
        if data["event"] == "media":
            if user_turn:
                # print('user talking')
                media = data["media"]
                chunk = base64.b64decode(media["payload"])
                bridge.add_data(chunk)
            else:
                # print('user not talking')
                try:
                    for val in generator:
                        media_stream = get_encoded_payload(val)
                            # Do something with the value (e.g., send it through the WebSocket)
                        media_data = {
                            "event": "media",
                            "streamSid": sid,
                            "media": {
                                "payload": media_stream,
                            }
                        }
                        ws.send(json.dumps(media_data))
                except StopIteration:
                    print("Generator completed")
                user_turn = True
        if data["event"] == "stop":
            print(f"Media WS: Received event 'stop': {message}")
            print("Stopping...")
            break

        
            

    bridge.terminate()
    print("WS connection closed")


if __name__ == "__main__":
    from gevent import pywsgi
    from geventwebsocket.handler import WebSocketHandler

    server = pywsgi.WSGIServer(
        ("", HTTP_SERVER_PORT), app, handler_class=WebSocketHandler
    )
    print("Server listening on: http://localhost:" + str(HTTP_SERVER_PORT))
    server.serve_forever()
