from SpeechExecutorBridge import SpeechExecutorBridge

s = SpeechExecutorBridge()

initial_messages = 'Hi! '
final_message = 'Alrighty then! This was fun, let\'ts do it again sometime haha!'

# s.speak(initial_message, 'initial')
s.speak(final_message, 'final')