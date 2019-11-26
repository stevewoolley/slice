import json

LOG_FORMAT = '%(asctime)s %(filename)-15s %(funcName)-15s %(levelname)-8s %(message)s'
AllowedActions = ['both', 'publish', 'subscribe']
TOPIC_STATUS_ON = ['1', 'on']
TOPIC_STATUS_OFF = ['0', 'off']
TOPIC_STATUS_TOGGLE = ['toggle']
TOPIC_STATUS_PULSE = ['blink', 'pulse']


def topic_parser(prefix, message_topic):
    return message_topic.replace('{}/'.format(prefix), '').split('/')


def iot_thing_topic(thing):
    return "$aws/things/{}/shadow/update".format(thing)


def iot_payload(target, doc):
    return json.dumps({'state': {target: doc}})
