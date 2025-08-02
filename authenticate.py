from kiteconnect import KiteConnect
import webbrowser

api_key = "m03pvkl6d69rs5g6"  # Replace!
api_secret = "9hbk4qm0ogpl36ys17iecjsvp4clcesd"  # Replace!

kite = KiteConnect(api_key=api_key)
login_url = kite.login_url()
print("Open this URL in browser and login:", login_url)
webbrowser.open(login_url)

request_token = input("After login, copy 'request_token' from URL and paste here: ")
data = kite.generate_session(request_token, api_secret=api_secret)
access_token = data["access_token"]
print("Your access token:", access_token)

with open("access_token.txt", "w") as f:
    f.write(access_token)