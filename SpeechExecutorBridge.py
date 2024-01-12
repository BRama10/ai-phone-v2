import os
import azure.cognitiveservices.speech as speechsdk
import string, random

def generate_random_string():
    """Generate a random 10-character string."""
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(10))

class SpeechExecutorBridge:
    def __init__(self):
        self.speech_config = speechsdk.SpeechConfig(subscription='60e5efd485b64bf78aee24ccd9874b47', region='eastus')
        self.speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Riff24Khz16BitMonoPcm)

        self.audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)

        self.speech_config.speech_synthesis_voice_name='en-US-SaraNeural'

        self.speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=self.speech_config, audio_config=None)

    def speak(self, text, title = None):
        speech_synthesis_result = self.speech_synthesizer.speak_text_async(text).get()
        # print(speech_synthesis_result.cancellation_details.reason)
        stream = speechsdk.AudioDataStream(speech_synthesis_result)
        if title == None:
            fn = generate_random_string()
        else:
            fn = title
        stream.save_to_wav_file(f'{fn}.wav')
        return fn
        # return speech_synthesis_result.reason
        
