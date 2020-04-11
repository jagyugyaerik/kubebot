import json
import os

from slack import RTMClient

from db import select_app, update_app, init_db


def find_pod(user: str):
    app, namespace = select_app(user)
    if app is not None:
        pod, result = get_pod(app, namespace)
        return {
            'namespace': namespace,
            'app': app,
            'pod': pod
        }
    return None


def logs_command(conv, tokens):
    if len(tokens) > 0:
        user = tokens[0]
    else:
        user = f'<@{conv.user}>'  # command sender

    result = find_pod(user)
    if result is None:
        return f"No app has been set for {user} "  # yeah, error handling should be better here

    return logs(result['pod'], result['namespace'])


def describe_command(conv, tokens):
    if len(tokens) > 0:
        user = tokens[0]
    else:
        user = f'<@{conv.user}>'  # command sender

    result = find_pod(user)
    if result is None:
        return f"No app has been set for {user} "  # yeah, error handling should be better here

    return describe(result['pod'], result['namespace'])


def get_app_command(conv, tokens):
    if len(tokens) > 0:
        user = tokens[0]
    else:
        user = f'<@{conv.user}>'  # command sender

    result = find_pod(user)
    if result is not None:
        return f"Current app for {user} is {result['app']} (currently at {result['pod']})"
    return f"No app has been set for {user}"


def set_app_command(conv, tokens):
    if len(tokens) < 3:
        return 'Unable to understand, please message with set-app <@user> <application> <namespace>'
    else:
        user = tokens[0]
        app = tokens[1]
        namespace = tokens[2]

        pod, result = get_pod(app, namespace)
        if len(result['items'][0]['spec']['containers']) > 1:
            return f'Application {app} has multiple containers'  # todo: allow container selection
        update_app(app, namespace, user)

        return f"Successfully set app for {user} to {app} (currently at pod {pod})"


def get_pod(app, namespace):
    cmd = f'kubectl get pods --selector=app={app} --namespace={namespace} -ojson'
    print(f'Executing {cmd}')
    stream = os.popen(cmd)
    result = json.loads(stream.read())
    if len(result['items']) == 0:
        raise Exception(f'{app} not found in {namespace}')
    pod = result['items'][0]['metadata']['name']
    return pod, result


def logs(pod, namespace):
    cmd = f'kubectl logs  {pod} --namespace={namespace}'
    print(f'Executing {cmd}')
    stream = os.popen(cmd)
    return stream.read()


def describe(pod, namespace):
    cmd = f'kubectl describe pod {pod} --namespace={namespace}'
    print(f'Executing {cmd}')
    stream = os.popen(cmd)
    return stream.read()


commands = {
    'logs': logs_command,
    'describe': describe_command,
    'get-app': get_app_command,
    'set-app': set_app_command
}


class Conversation:
    def __init__(self, web_client, channel, user):
        self.web_client = web_client
        self.channel = channel
        self.user = user

    def msg(self, text):
        # self.web_client.chat_postEphemeral(
        #     channel= self.channel,
        #     user=self.user,
        #     text=text,
        #
        # )
        self.web_client.chat_postMessage(
            channel=self.channel,
            text=text,

        )


welcome = '''
Hi there <@{user}>. I'm your friendly neighbourhood DevOps bot.
Use _{me} set-app @user application namespace_ to set the current app for a user
Use _{me} get-app @user_ to get the current app (or leave user out for the current user)
Use _{me} logs_ to get the logs for the app that is set for the current user 
Use _{me} describe_ to get the description for the app that is set for the current user 
'''


@RTMClient.run_on(event="message")  # subscribe to 'message' events
def process_command(**payload):
    data = payload['data']
    web_client = payload['web_client']
    print(payload)
    # ignore service messages, like joining a channel
    is_service = 'subtype' in data and data['subtype'] is not None

    if not is_service and 'text' in data:
        channel_id = data['channel']
        thread_ts = data['ts']
        user = data['user']
        text = data['text']  # get data from the event
        tokens = text.split()  # split it up by space characters
        me = tokens[0]  # user id of the cht bot
        # object to track the conversation state
        conv = Conversation(web_client, channel_id, user)
        if len(tokens) > 1:
            print(tokens)
            # first token is my userid, second will be the command e.g. logs
            command = tokens[1]
            print('received command ' + command)
            if command in commands:
                # get the actual command executor
                command_func = commands[command]
                try:
                    args = tokens[slice(2, len(tokens))]
                    # execute the command
                    result = command_func(conv, args)
                    if result is not None:
                        # and return the value from the
                        # command back to the user
                        conv.msg(result)
                except Exception as e:
                    conv.msg(str(e))

            else:
                # show welcome message
                web_client.chat_postMessage(
                    conv.msg(welcome.format(user=user, me=me))
                )
        else:
            # show welcome message
            conv.msg(welcome.format(user=user, me=me))


def main():
    init_db()
    slack_token = os.environ["SLACK_API_TOKEN"]
    rtm_client = RTMClient(token=slack_token)
    rtm_client.start()


if __name__ == "__main__":
    main()
