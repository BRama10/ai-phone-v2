import os
from twilio.rest import Client
import time
from constants import PHONE_NUMBERS

account_sid = None
auth_token = None
client = Client(account_sid, auth_token)

#export name const
NAME = 'Grace'

if __name__ == '__main__':
    call = client.calls.create(
                            url='https://65d9-71-127-43-49.ngrok-free.app/twiml',
                            to=f'+1{PHONE_NUMBERS.get(NAME)}',
                            from_='+18336599785',
                            # machine_detection='DetectMessageEnd',
                            # async_amd='false',
                            # async_amd_status_callback='https://6dfa-71-127-43-49.ngrok-free.app/response'
                            # status_callback='https://6dfa-71-127-43-49.ngrok-free.app/response',
                            # status_callback_event=['initiated', 'completed']
                        )

    print('Answered By', call.answered_by)