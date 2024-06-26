import queue
import azure.cognitiveservices.speech as speechsdk
import numpy as np

SUBSCRIPTION = None
REGION = None

class SpeechClientBridge:
    def __init__(self, on_response):
        self._queue = queue.Queue()
        self._ended = False
        
        config = speechsdk.SpeechConfig(subscription=SUBSCRIPTION, region=REGION)
        config.set_property(speechsdk.PropertyId.Speech_SegmentationSilenceTimeoutMs, "1700")
        config.set_profanity(speechsdk.ProfanityOption.Raw)
        audio_format = speechsdk.audio.AudioStreamFormat(samples_per_second=8000,
                                                     bits_per_sample=8,
                                                     channels=1,
                                                     wave_stream_format=speechsdk.AudioStreamWaveFormat.MULAW)
        self.stream = speechsdk.audio.PushAudioInputStream(stream_format=audio_format)
        self.audio_config = speechsdk.audio.AudioConfig(stream=self.stream)
        speechsdk.PropertyId
        self.speech_recognizer = speechsdk.SpeechRecognizer(speech_config=config, audio_config=self.audio_config)

        self.new_user_query = on_response


    def session_stopped_cb(self, evt):
        """callback that signals to stop continuous recognition upon receiving an event `evt`"""
        print('SESSION STOPPED: {}'.format(evt))
        print('CALLED')
        self.terminate()
        # recognition_done.set()

    def recognize_result(self, evt,):
       text = evt.result.text
       self.new_user_query(text)

    def add_data(self, chunk):
        self.stream.write(chunk)

    def start(self):
        self.speech_recognizer.recognizing.connect(lambda evt: print('RECOGNIZING: {}'.format(evt)))
        self.speech_recognizer.recognized.connect(self.recognize_result)
        self.speech_recognizer.session_started.connect(lambda evt: print('SESSION STARTED: {}'.format(evt)))
        self.speech_recognizer.session_stopped.connect(self.session_stopped_cb)
        self.speech_recognizer.canceled.connect(lambda evt: print('CANCELED {}'.format(evt)))
        
        self.speech_recognizer.start_continuous_recognition()
        

    def terminate(self):
        self.stream.close()
        self._ended = True
        self.speech_recognizer.stop_continuous_recognition()
