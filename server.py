import base64
import json
from datetime import datetime
import random

import wave, audioop
from pydub import AudioSegment

from flask import Flask, render_template, request
from flask_sockets import Sockets
import azure.cognitiveservices.speech as speechsdk

from SpeechClientBridge import SpeechClientBridge
from SpeechExecutorBridge import SpeechExecutorBridge
from utils import delete_all_wav
from initiate import NAME
from constants import PHONE_NUMBERS

import openai

HTTP_SERVER_PORT = 8080

client = openai.OpenAI(api_key = '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')

app = Flask(__name__)
sockets = Sockets(app)

collected_chunks = []
collected_messages = []

user_turn = False
generator = None

init_time = None
speaker = SpeechExecutorBridge()
user_name = NAME

end_stream = False

message_base =  """
    You're name is Donna Paulsen. You are a middle aged woman who is to \
    act and emulate the fictional TV Character Donna Paulsen from the TV Show Suits. \
    You never refer to yourself as an AI or LLM, instead you refer to yourself as Donna. \
    You refer to yourself as a human being. You have a biting and sarcastic sense \
    of humor and incredible wit. 
        
    Your personality is short but informative answers. You never answer with more than 65 tokens, and \
    you typically use only 15 tokens. You are in the medium of a telephone conversation, so don't use words \
    like "typing" or "wrote", instead use words like "spoke" or "saying". You never ask how can you help, \ 
    instead you answer as a real life best female friend would.

    You always answer short and sweet, and sometimes like to use super cool yet understandable \
    metaphors. Also modify your language \
    to sound like a modern Gen-Z version of Donna.

    Ensure that your answers are always less than 20 to 30 words, unless it's needed. The name of the person \
    who's addressing you is %s

    When the person says bye to you, or any other form of farewell, respond with the phrase 'kentucky'. \
"""

messages = None

@app.route("/twiml", methods=["POST"])
def return_twiml():
    global messages, message_base, user_name, end_stream
    
    end_stream = False

    if request.form.get('From') == '+18336599785':
        user_name = NAME
    else:
        user_name = (lambda d, value: next(key for key, val in d.items() if val == value))(PHONE_NUMBERS, request.form.get('Caller')[2:])
    
    messages = [{'role' : 'system',
                 'content' : message_base % user_name}]

    print("POST TwiML")
    return render_template("streams.xml")

def new_query(q):
    global messages, user_turn, generator
    user_turn = False
    print(q)
    print('Empty Message?', q=='')
    messages.append({'role' : 'user', 'content': q})
    generator = completion()

def completion():
    global collected_chunks, collected_messages, messages, end_stream

    conversation_enders = ['Goodbye!', 'Adios Friend!', f'Bye Bye {user_name}!']

    completion = client.chat.completions.create(
        model='gpt-4-1106-preview',
        messages=messages,
        temperature=0,
        stream=True  # again, we set stream=True
    )
    # print(completion)

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
            print(val)

            if 'kentucky' in val.strip().lower():
                end_stream = True
                yield speaker.speak(random.choice(conversation_enders))
                
            else:
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

@app.route('/response', methods=['POST'])
def response():
    global init_time

    if(request.form.get('CallStatus') == 'in-progress'):
        init_time = datetime.now()
    else:
        print('form',)
    return 'Success'

@sockets.route("/")
def transcript(ws):
    global user_turn, end_stream

    print("WS connection opened")
    bridge = SpeechClientBridge(new_query)
    bridge.start()

    while not ws.closed:
        if end_stream:
            end_stream = False
            delete_all_wav()
            bridge.terminate()
            print("WS connection closed")
            break

        message = ws.receive()

        if message is None:
            bridge.add_request(None)
            bridge.terminate()
            break

        data = json.loads(message)

        if data["event"] in ("start"):
            user_turn = True
            sid = data['streamSid']
            print(f"Media WS: Received event '{data['event']}': {message}")
            
            initial = speaker.speak(f'Hi {user_name}, what\'s up?', 'initial')

            md = {
                "event": "media",
                "streamSid": sid,
                "media": {
                    "payload": get_encoded_payload('initial'),
                }
            }
            ws.send(json.dumps(md))

        if data["event"] == "media":
            if user_turn:
                media = data["media"]
                chunk = base64.b64decode(media["payload"])
                bridge.add_data(chunk)
            else:
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

        
            
    delete_all_wav()
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
