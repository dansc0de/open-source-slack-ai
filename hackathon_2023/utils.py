import re

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

_id_name_cache = {}


async def get_channel_history(client: WebClient, channel_id: str) -> list:
    try:
        response = client.conversations_history(channel=channel_id, limit=1000)  # 1000 is the max limit
        bot_id = await get_bot_id(client)  # fixme: this doesn't work
        # todo: exclude messages that start with `/` (i.e. slash commands)
        # todo: support excluding other bots too
        return [msg for msg in response["messages"] if msg.get("bot_id") != bot_id]
    except SlackApiError as e:
        print(f"Error fetching history: {e.response['error']}")
        return []


async def get_bot_id(client) -> str:
    """
    Retrieves the bot ID using the provided Slack WebClient.

    Returns:
        str: The bot ID.
    """
    try:
        response = client.auth_test()
        return response["user_id"]
    except SlackApiError as e:
        print(f"Error fetching bot ID: {e.response['error']}")
        return 'None'


def get_name_from_id(client: WebClient, user_or_bot_id: str) -> str:
    """
    Retrieves the name associated with a user ID or bot ID.

    Args:
        client (WebClient): An instance of the Slack WebClient.
        user_or_bot_id (str): The user or bot ID.

    Returns:
        str: The name associated with the ID.
    """
    if user_or_bot_id in _id_name_cache:
        return _id_name_cache[user_or_bot_id]

    try:
        user_response = client.users_info(user=user_or_bot_id)
        if user_response.get("ok"):
            _id_name_cache[user_or_bot_id] = user_response["user"]["real_name"]
            return user_response["user"]["real_name"]
        else:
            print('user fetch failed')
            raise SlackApiError("user fetch failed", user_response)
    except SlackApiError as e:
        if e.response["error"] == "user_not_found":
            try:
                bot_response = client.bots_info(bot=user_or_bot_id)
                if bot_response.get("ok"):
                    _id_name_cache[user_or_bot_id] = bot_response["bot"]["name"]
                    return bot_response["bot"]["name"]
                else:
                    print('bot fetch failed')
                    raise SlackApiError("bot fetch failed", bot_response)
            except SlackApiError as e:
                print(f"Error fetching name for bot {user_or_bot_id=}: {e.response['error']}")
        print(f"Error fetching name for {user_or_bot_id=}: {e.response['error']}")

    return 'Someone'


async def get_direct_message_channel_id(client: WebClient) -> str:
    """
    Get the direct message channel ID for the bot, so you can say() via direct message.
    :return str:
    """
    try:
        # response = client.conversations_open(users=[await get_bot_id(client)])
        print('fixme: getting DM channel ID using hardcoded value')
        # user_id = client.auth_test()['user_id']  # fixme: this is getting the bot user!

        user_id = 'UPU1WE23F'  # fixme: hardcoded with Bryce's user ID for now
        response = client.conversations_open(users=user_id)
        return response["channel"]["id"]
    except SlackApiError as e:
        print(f"Error fetching bot DM channel ID: {e.response['error']}")
        raise e


def parse_messages(client, messages):
    def parse_message(msg):
        name = get_name_from_id(client, msg.get("user", msg.get("bot_id")))
        parsed_message = re.sub(r'<@U\w+>', lambda m: get_name_from_id(client, m.group(0)[2:-1]), msg["text"])
        return f'{name}: {parsed_message}'

    return [parse_message(message) for message in messages]