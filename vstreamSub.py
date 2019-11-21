#!/usr/bin/env python

from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
# import AWSIoTPythonSDK.exception.AWSIoTExceptions
import argparse
import logging
import time
import platform
from iot import topic_parser, iot_thing_topic, iot_payload
import supervised

AllowedActions = ['both', 'publish', 'subscribe']
LOG_FORMAT = '%(asctime)s %(filename)-15s %(funcName)-15s %(levelname)-8s %(message)s'


# def status():
#     try:
#         processes = server.supervisor.getAllProcessInfo()
#         procs = {}
#         for s in processes:
#             procs[s['name']] = s['statename']
#         logger.info("supervised: {}".format(processes))
#         myAWSIoTMQTTClient.publish(iot_thing_topic(args.thingName), iot_payload('reported', procs), 0)
#     except AWSIoTPythonSDK.exception.AWSIoTExceptions.publishTimeoutException:
#         logger.warning("publish timeout")
#     except Exception as e:
#         logger.error(e)


def subscriptionCallback(client, userdata, message):
    logger.info("{} {}".format(message.topic, message.payload))
    params = topic_parser(args.topic, message.topic)
    supervisor = supervised.Supervised('vstream')
    if params[0] == 'status' and len(params) == 1:
        myAWSIoTMQTTClient.publish(iot_thing_topic(args.thingName),
                                   iot_payload('reported', {'status': supervisor.status()}), 0)
    elif params[0] == 'start' and len(params) == 1:
        supervisor.start()
    elif params[0] == 'stop' and len(params) == 1:
        supervisor.stop()


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
    logger = logging.getLogger('vstreamSub')
    streamHandler = logging.StreamHandler()
    logger.addHandler(streamHandler)

    # supervisor rpc

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

    while True:
        time.sleep(1)
