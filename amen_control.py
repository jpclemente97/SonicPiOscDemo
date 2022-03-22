import numpy as np
import joblib
from sklearn import *
from pythonosc import dispatcher, osc_server, udp_client
import asyncio

# Restoring our regressor model from a file
joblib_file = "./data/mlp_model.pkl"
mlp = joblib.load(joblib_file)

# Initializing variables
acc_vect = np.zeros((1,3))
cutoff, rate = 100, 0.5

# Creating a function that will handle and push accelerometer through the regressor
def acceleration_vector(address, args):
    global cutoff, rate
    if address.find('accelerometer/x') != -1:
        acc_vect[0,0] = args
    elif address.find('accelerometer/y') != -1:
        acc_vect[0,1] = args
    elif address.find('accelerometer/z') != -1:
        acc_vect[0,2] = args
        pred = mlp.predict(acc_vect)
        print('Cutoff:    %.1f'%cutoff, '\tRate:    %.3f' %rate)

        # Scaling the values sent to Sonic Pi
        cutoff = (pred.flat[0] + 1) * 50
        cutoff = int(cutoff)
        if cutoff > 130: cutoff = 130
        rate = (pred.flat[1] + 1) / 2
        rate = np.fmax(rate, 0.001)
        rate = np.fmin(rate, 1)

# Attaching the function to the dispatcher
dispatcher = dispatcher.Dispatcher()
dispatcher.map("/accelerometer/*", acceleration_vector)


# Aking user for IP and OSCHook ports
ip = str(input("\n\n\nWhat is your IP adress? \n> "))
print("\nIP adress:", ip)
phone_port = int(input("\n\nWhat is OSCHooks (UDP) Port? \n> "))
print("\nOSCHook Port:", phone_port)

# Sonic Pi uses UDP 4560 by default
sonic_port = 4560

# Asking for how long the user want to control the app (in seconds or forever)
control_time = input("\n\nHow many seconds will you run this server? (Leave blank for forever)\n> ")
if control_time == "":
    control_time = 0
elif int(control_time) > 0:
    control_time = int(control_time) * 1000
print("")


# Sender (UDPClient) handling messages to Sonic Pi
sender = udp_client.SimpleUDPClient(ip, sonic_port)


# Async main loop for sending messages to Sonic Pi
async def loop(control_time=False):

    # Loop running for as many seconds as the user specified
    if control_time > 0:
        for i in range(control_time):
            sender.send_message('/control/amen', [cutoff, rate])
            await asyncio.sleep(0.001)

    # Loop running forever
    else:
        while True:
            sender.send_message('/control/amen', [cutoff, rate])
            await asyncio.sleep(0.001)


# Initializing of server event loop for grabbing OSC from phone
async def init_main():
    server = osc_server.AsyncIOOSCUDPServer((ip, phone_port), dispatcher, asyncio.get_event_loop())
    transport, protocol = await server.create_serve_endpoint()  # Create datagram endpoint and start serving

    await loop(control_time)  # Enter main loop of program

    transport.close()  # Clean up serve endpoint


# AsyncIO loop handling both OSC server (from phone) and OSC messages (to Sonic Pi)
asyncio.run(init_main())