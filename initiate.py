import os
from twilio.rest import Client
import subprocess

packages = ['twillio']

for package in packages:
    try:
        subprocess.run(['pip', 'show', package], check=True)
        subprocess.run(['pip', 'install', '--upgrade', package], check=True)
    except subprocess.CalledProcessError:
        subprocess.run(['pip', 'install', package], check=True)

#put yo phone number oer here
PHONE_NUMBER = '7034029151'

account_sid = 'AC4264783504bd05570b278f2ce045b2c9'
auth_token = '688e178cb124c53cdfe81ba15a9442a0'
client = Client(account_sid, auth_token)

call = client.calls.create(
                        url='https://57f2-71-127-43-49.ngrok-free.app/twiml',
                        to=f'+1{PHONE_NUMBER}',
                        from_='+18336599785'
                    )