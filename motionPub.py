#!/usr/bin/env python

from iot import AllowedActions, LOG_FORMAT
import platform
import argparse
from signal import pause
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
from gpiozero import MotionSensor
import logging
import json


def motion():
    logging.info('Motion')
    try:
        myAWSIoTMQTTClient.connect()
        myAWSIoTMQTTClient.publish(args.topic, json.dumps({'thing': args.thingName}), 0)
        myAWSIoTMQTTClient.disconnect()
    except Exception as err:
        logging.warning('{}'.format(err))


def no_motion():
    logging.info('No Motion')


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
    parser.add_argument("-id", "--clientId", action="store", dest="clientId", default="vstreamSub",
                        help="Targeted client id")
    parser.add_argument("-m", "--mode", action="store", dest="mode", default="both",
                        help="Operation modes: %s" % str(AllowedActions))
    parser.add_argument("-t", "--topic", action="store", dest="topic", default="sdk/test/Python", help="Targeted topic")
    parser.add_argument("-n", "--thingName", action="store", dest="thingName", default=platform.node().split('.')[0],
                        help="Targeted thing name")
    parser.add_argument("--pin", action="store", dest="pin", help="gpio pin (using BCM numbering)", type=int)
    parser.add_argument("-q", "--queue_len",
                        help="The length of the queue used to store values read from the sensor. (1 = disabled)",
                        type=int, default=1)
    parser.add_argument("--sample_rate",
                        help="The number of values to read from the device " +
                             "(and append to the internal queue) per second",
                        type=float, default=100)
    parser.add_argument("-x", "--threshold",
                        help="When the mean of all values in the internal queue rises above this value, " +
                             "the sensor will be considered active by the is_active property, " +
                             "and all appropriate events will be fired",
                        type=float, default=0.5)
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
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

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

    pir = MotionSensor(args.pin, queue_len=args.queue_len, sample_rate=args.sample_rate, threshold=args.threshold)

    pir.when_motion = motion
    pir.when_no_motion = no_motion

    pause()
