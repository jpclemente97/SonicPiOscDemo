import numpy as np
import pandas as pd
import sklearn
from sklearn import *
from IPython.display import clear_output

from pythonosc import dispatcher
from pythonosc import osc_server
from pythonosc import osc_message_builder
from pythonosc import udp_client

import asyncio


#### read dataset
dataset = pd.read_csv('./data/data.csv')

#importing the columns with accelerometer (gravity) data on the three exis
rawdata = dataset[['x', 'y', 'z']].to_numpy()
inputs = np.empty((0,3))
target = np.empty((inputs.shape[0],2))

#iterating through the entries of the dataset and creating associated target values
#the index edges for the postures have been found manually by visually inspecting the waveforms
for i in range(0,rawdata.shape[0]):
    if (2 <= i <= 1025):
        inputs = np.append(inputs, rawdata[i,:].reshape(1,-1), axis=0)
        target = np.append(target, np.array([[1.,1.]]), axis=0) #looking at phone
    elif (1052 <= i <= 1990):
        inputs = np.append(inputs, rawdata[i,:].reshape(1,-1), axis=0)
        target = np.append(target, np.array([[1.,0.]]), axis=0) #face level to the left
    elif (2007 <= i <= 3010):
        inputs = np.append(inputs, rawdata[i,:].reshape(1,-1), axis=0)
        target = np.append(target, np.array([[0.,1.]]), axis=0) #face level upwards
    elif (3050 <= i <= 3937):
        inputs = np.append(inputs, rawdata[i,:].reshape(1,-1), axis=0)
        target = np.append(target, np.array([[0.,0.]]), axis=0) #face level downwards


#creating train/test split
inputs_train, inputs_test, target_train, target_test = sklearn.model_selection.train_test_split(inputs, target, test_size=0.1)

#training the model
mlp = sklearn.neural_network.MLPRegressor(hidden_layer_sizes=(8,4), max_iter=20000, activation='logistic')
mlp.fit(inputs_train, target_train)
target_predict =  mlp.predict(inputs_test)


#print the number of misclassified samples, accuracy and complete report (using scikit learn metric tools) 
print('r2 score on individual targets',sklearn.metrics.r2_score(target_test, target_predict, multioutput='raw_values'))


acc_vect = np.zeros((1,3))
cutoff, rate = 0, 0

#creating a function that will handle and push accelerometer through the regressor
def acceleration_vector(address, args):
    global cutoff, rate
    if address.find('accelerometer/x') != -1:
        acc_vect[0,0] = args
    elif address.find('accelerometer/y') != -1:
        acc_vect[0,1] = args
    elif address.find('accelerometer/z') != -1:
        acc_vect[0,2] = args
        clear_output(wait=True)
        pred = mlp.predict(acc_vect)
        print('Parameters   %.3f'%pred.flat[0], '  %.3f' %pred.flat[1])
        cutoff = (pred.flat[0] + 1) * 50
        cutoff = int(cutoff)
        rate = round(pred.flat[1], 3)

#attaching the function to the dispatcher
dispatcher = dispatcher.Dispatcher()
dispatcher.map("/accelerometer/*", acceleration_vector)



ip = "192.168.0.10"
sonic_port = 4560
phone_port = 8001

sender = udp_client.SimpleUDPClient(ip, sonic_port)


async def loop():
    """Example main loop that only runs for 10 iterations before finishing"""
    for i in range(1000):
        #print(f"Loop {i}")
        sender.send_message('/control/amen', [cutoff, rate])
        await asyncio.sleep(0.01)


async def init_main():
    server = osc_server.AsyncIOOSCUDPServer((ip, phone_port), dispatcher, asyncio.get_event_loop())
    transport, protocol = await server.create_serve_endpoint()  # Create datagram endpoint and start serving

    await loop()  # Enter main loop of program

    transport.close()  # Clean up serve endpoint


asyncio.run(init_main())