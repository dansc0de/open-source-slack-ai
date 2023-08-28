import os
import openai
import re

from dotenv import load_dotenv

load_dotenv()
CHAT_MODEL = str(os.environ.get('CHAT_MODEL') or "gpt-3.5-turbo").strip()
DEBUG = bool(os.environ.get('DEBUG', False))
LANGUAGE = 'English'
MAX_BODY_TOKENS = 3000
OPEN_AI_TOKEN = str(os.environ.get('OPEN_AI_TOKEN')).strip()
TEMPERATURE = float(os.environ.get('TEMPERATURE') or 0.2)

if OPEN_AI_TOKEN == "":
    raise ValueError("OPEN_AI_TOKEN is not set in .env file")

openai.api_key = OPEN_AI_TOKEN


def summarize(text: str, language: str = LANGUAGE):
    """
    Summarize a chat log in bullet points, in the specified language.

    Args:
        text (str): The chat log to summarize, in the format "Speaker: Message" separated by line breaks.
        language (str, optional): The language to use for the summary. Defaults to LANGUAGE.

    Returns:
        str: The summarized chat log in bullet point format.

    Examples:
        # >>> summarize("Alice: Hi\nBob: Hello\nAlice: How are you?\nBob: I'm doing well, thanks.")
        '- Alice greeted Bob.\n- Bob responded with a greeting.\n- Alice asked how Bob was doing.
        \n- Bob replied that he was doing well.'
    """
    response = openai.ChatCompletion.create(
        model=CHAT_MODEL,
        temperature=TEMPERATURE,
        messages=[{
            "role":
                "system",
            "content":
                "\n".join([
                    'You\'re a highly capable summarization expert who provides succinct summaries of Slack chat logs.',
                    'The chat log format consists of one line per message in the format "Speaker: Message".',
                    "The `\\n` within the message represents a line break."
                    f'The user understands {language} only.',
                    f'So, The assistant needs to speak in {language}.',
                ])
        }, {
            "role":
                "user",
            "content":
                "\n".join([
                    f"Please summarize the following chat log to a flat bullet list.",
                    "Do not write a line by line summary. Instead, summarize the overall conversation.",
                    "Do not include greeting/salutation/polite expressions in summary.",
                    "Make the summary easy to read while maintaining a conversational tone and retaining meaning."
                    f"Write in conversational {language}.", "", text
                ])
        }])

    if DEBUG:
        print(response["choices"][0]["message"]['content'])
    return response["choices"][0]["message"]['content']


def estimate_openai_chat_token_count(text: str) -> int:
    """
    Estimate the number of OpenAI API tokens that would be consumed by sending the given text to the chat API.

    Args:
        text (str): The text to be sent to the OpenAI chat API.

    Returns:
        int: The estimated number of tokens that would be consumed by sending the given text to the OpenAI chat API.

    Examples:
        >>> estimate_openai_chat_token_count("Hello, how are you?")
        7
    """
    # Split the text into words and count the number of characters of each type
    pattern = re.compile(
        r"""(
            \d+       | # digits
            [a-z]+    | # alphabets
            \s+       | # whitespace
            .           # other characters
            )""", re.VERBOSE | re.IGNORECASE)
    matches = re.findall(pattern, text)

    # based on https://help.openai.com/en/articles/4936856-what-are-tokens-and-how-to-count-them
    def counter(tok):
        if tok == ' ' or tok == '\n':
            return 0
        elif tok.isdigit() or tok.isalpha():
            return (len(tok) + 3) // 4
        else:
            return 1

    return sum(map(counter, matches))


def split_messages_by_token_count(messages: list[dict]) -> list[list[str]]:
    """
    Split a list of strings into sub lists with a maximum token count.

    Args:
        messages (list[str]): A list of strings to be split.

    Returns:
        list[list[str]]: A list of sub lists, where each sublist has a token count less than or equal to max_body_tokens.
    """
    # todo: get the username from `user` (the user id)
    # todo: get the bot name from the bot_id
    message_texts = [f'{msg.get("user", msg.get("bot_id"))}: {msg["text"]}' for msg in messages]

    body_token_counts = [estimate_openai_chat_token_count(msg) for msg in message_texts]
    result = []
    current_sublist = []
    current_count = 0

    for message, count in zip(message_texts, body_token_counts):
        if current_count + count <= MAX_BODY_TOKENS:
            current_sublist.append(message)
            current_count += count
        else:
            result.append(current_sublist)
            current_sublist = [message]
            current_count = count

    result.append(current_sublist)
    return result


def summarize_slack_messages(messages: list) -> list:
    result_text = []

    for split_messages in split_messages_by_token_count(messages):
        text = summarize("\n".join(split_messages), LANGUAGE)
        result_text.append(text)

    return result_text


def main():
    print('let\'s summarize!')


if __name__ == '__main__':
    main()