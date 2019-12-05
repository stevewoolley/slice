#!/usr/bin/env python

from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import argparse
import time
import platform
from iot import topic_parser, iot_thing_topic, iot_payload, AllowedActions, LOG_FORMAT
import supervised
import logging

def publish(key, value, state='reported', qos=0):
    myAWSIoTMQTTClient.publish(
        iot_thing_topic(args.thingName),
        iot_payload(state, {key: value}), qos)


def subscriptionCallback(client, userdata, message):
    global countdown
    params = topic_parser(args.topic, message.topic)
    if params[0] == 'start' and len(params) == 1 and supervisor.status() == 'STOPPED':
        supervisor.start()
    elif params[0] == 'stop' and len(params) == 1 and supervisor.status() == 'RUNNING':
        supervisor.stop()
    elif params[0] == 'pulse' and len(params) == 2:
        if supervisor.status() == 'STOPPED':
            supervisor.start()
        if params[1].isdigit() and countdown < int(params[1]):
            countdown = int(params[1])


if __name__ == "__main__":
    # Read in command-line parameters
    parser = argparse.ArgumentParser()
    parser.add_argument("-e", "--endpoint", action="store", required=True, dest="host",
                        help="Your AWS IoT custom endpoint")
    parser.add_argument("-r", "--rootCA", action="store", required=True, dest="rootCAPath", help="Root CA file path")
    parser.add_argument("-c", "--cert", action="store", dest="certificatePath", help="Certificate file path")
    parser.add_argument("-k", "--key", action="store", dest="privateKeyPath", help="Private key file path")
    parser.add_argument("-p", "--port", action="store", dest="port", type=int, help="Port number override")
    parser.add_argument("-w", "--websocket", action="store_true", dest="useWebsocket", default=False,
                        help="Use MQTT over WebSocket")
    parser.add_argument("-id", "--clientId", action="store", dest="clientId", default="",
                        help="Targeted client id")
    parser.add_argument("-m", "--mode", action="store", dest="mode", default="both",
                        help="Operation modes: %s" % str(AllowedActions))
    parser.add_argument("-t", "--topic", action="store", dest="topic", default="sdk/test/Python", help="Targeted topic")
    parser.add_argument("-s", "--service", action="store", dest="service", default="vstream", help="Service name")
    parser.add_argument("-n", "--thingName", action="store", dest="thingName", default=platform.node().split('.')[0],
                        help="Targeted thing name")
    args = parser.parse_args()

    if args.mode not in AllowedActions:
        parser.error("Unknown --mode option %s. Must be one of %s" % (args.mode, str(AllowedActions)))
        exit(2)

    if args.useWebsocket and args.certificatePath and args.privateKeyPath:
        parser.error("X.509 cert authentication and WebSocket are mutual exclusive. Please pick one.")
        exit(2)

    if not args.useWebsocket and (not args.certificatePath or not args.privateKeyPath):
        parser.error("Missing credentials for authentication.")
        exit(2)

    # Port defaults
    port = args.port
    if args.useWebsocket and not args.port:  # When no port override for WebSocket, default to 443
        port = 443
    if not args.useWebsocket and not args.port:  # When no port override for non-WebSocket, default to 8883
        port = 8883

    # Configure logging
    logging.basicConfig(level=logging.WARN, format=LOG_FORMAT)

    # supervisor rpc
    supervisor = supervised.Supervised(args.service)
    state = supervisor.status()
    countdown = 0

    # Init AWSIoTMQTTClient
    myAWSIoTMQTTClient = None
    if args.useWebsocket:
        myAWSIoTMQTTClient = AWSIoTMQTTClient(args.clientId, useWebsocket=True)
        myAWSIoTMQTTClient.configureEndpoint(args.host, port)
        myAWSIoTMQTTClient.configureCredentials(args.rootCAPath)
    else:
        myAWSIoTMQTTClient = AWSIoTMQTTClient(args.clientId)
        myAWSIoTMQTTClient.configureEndpoint(args.host, port)
        myAWSIoTMQTTClient.configureCredentials(args.rootCAPath, args.privateKeyPath, args.certificatePath)

    # AWSIoTMQTTClient connection configuration
    myAWSIoTMQTTClient.configureAutoReconnectBackoffTime(1, 32, 20)
    myAWSIoTMQTTClient.configureOfflinePublishQueueing(-1)  # Infinite offline Publish queueing
    myAWSIoTMQTTClient.configureDrainingFrequency(2)  # Draining: 2 Hz
    myAWSIoTMQTTClient.configureConnectDisconnectTimeout(10)  # 10 sec
    myAWSIoTMQTTClient.configureMQTTOperationTimeout(5)  # 5 sec

    # Connect and subscribe to AWS IoT
    myAWSIoTMQTTClient.connect()
    if args.mode == 'both' or args.mode == 'subscribe':
        myAWSIoTMQTTClient.subscribe('{}/#'.format(args.topic), 1, subscriptionCallback)
        time.sleep(2)  # give service time to subscribe

    count = 0
    while True:
        count += 1
        time.sleep(1)
        if countdown == 1:
            supervisor.stop()
            countdown = 0
        else:
            countdown -= 1
        if count % 20 == 0:
            count = 0  # reset
            current_state = supervisor.status()
            if state != current_state:  # change detected
                state = current_state
                publish(supervisor.process, current_state)
