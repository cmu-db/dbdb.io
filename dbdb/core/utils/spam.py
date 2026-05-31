import re
from pprint import pprint

from ollama import chat

from dbdb.core.models import System


class UnexpectedResponseError(RuntimeError):
    pass

# Sometimes qwen outputs "**not spam**", so we can just treat that as a valid response
FUDGEY_RESPONSES_NOT_SPAM = [
    '**answer:** not spam',
    '**not spam**',
    'answer: false',
    'answer: not spam',
    '**answer:** false',
    '**answer:** no',
    '**answer:** `no`'
]
FUDGEY_RESPONSES_CORRECT_SUMMARIZE = [

]


def is_spam(
    html: str,
    system: System,
    *,
    model: str = "qwen3:8b", # "llama3.2",
    temperature: float = 0.2,
    timeout: int = 30,
) -> bool:
    """
    Use a local Ollama LLM to determine whether an HTML page has been taken over by spam
    instead of legitimately discussing the given database system.

    Args:
        html: Raw HTML content of the page.
        database_name: Name of the expected database system (e.g., "PostgreSQL").
        model: Ollama model name.
        ollama_url: Ollama chat API endpoint.
        timeout: HTTP timeout in seconds.

    Returns:
        True if the page is classified as spam, False otherwise.
    """

    assert len(html) > 0, "Empty HTML contents"

    system_prompt = (
        "You are a strict web page classifier.\n"
        "Your task is to decide whether a web page has been taken over by spam.\n"
        "You must output ONLY one word and no additional text: true or false.\n"
        "true  = the page is spam\n"
        "false = the page is not spam\n\n"
        "A page is SPAM if it primarily contains content such as:\n"
        "- Online gambling or betting.\n"
        "- Pornography or adult services\n"
        "- Online pharmacies or prescription drug sales.\n"
        "- Crypto or financial scams.\n"
        "- Online education, IT training, certifications.\n"
        "- SEO spam, link farms, or auto-generated keyword pages.\n"
        "- Domain parking pages (GoDaddy) or ads with no substantive content.\n\n"
        "The page is NOT spam if it primarily discusses technical or documentation-related information about the expected topic. "
        "If the page contains source code, then you assume it is for the database system and is not spam.\n"
        "Do not try to summarize or explain any code.\n"
        "Your answer must be in English even if the web page is in a different language.\n\n"
        "Ignore HTML tags, navigation menus, cookie banners, and generic ads.\n"
        "Focus on the semantic intent and dominant topic of the page.\n\n"
        # "You must output ONLY one word and no additional text: true or false.\n"
        # "true  = the page is spam\n"
        # "false = the page is not spam"
    ).strip()

    user_prompt = [ ]
    first_line = ""
    if system:
        # Add the system name and the developers (if they exist).
        # Adding the developer is useful for when pages talk about a company acquisition
        # but the name of the company is not the same as the database system (e.g., RedHat's etcd).
        first_line = f"The expected topic of this page is the database system '{system.name}'"
        developer_names = list(system.current().developer_orgs.values_list('name', flat=True))
        if developer_names:
            first_line += f" and/or {system.name}'s developers " + " and ".join(developer_names)
    else:
        first_line = "The expected topic of this page is about database systems"
    user_prompt = (
        f"{first_line}.\n\n"
        "Determine whether the following HTML page has been taken over by spam, "
        "rather than legitimately discussing this database system.\n\n"
        "HTML CONTENT START\n"
        f"{html[:12000]}\n"
        "HTML CONTENT END\n\n"
        "Answer:"
    )
    print(f"Invoking '{model}' run spam checker [system={system}]")
    answer = _run_prompt(system_prompt, user_prompt, model, temperature)

    if any(fr in answer for fr in FUDGEY_RESPONSES_NOT_SPAM):
        return False
    if answer not in {"true", "false"}:
        # If we don't get definitive answer, check whether at least the response
        # is a technical summarization of the system. If it is, then we can assume
        # that it is not spam
        if _check_response(answer, system, "mistral:7b", temperature):
            return False
        raise UnexpectedResponseError(f"Unexpected spam check LLM response [model={model} / temperature={temperature}]:\n{answer!r}")

    return answer == "true"

def _run_prompt(system_prompt: str, user_prompt: str, model: str, temperature: float):
    payload = [
        {"role": "system", "content": "".join(system_prompt)},
        {"role": "user", "content": "".join(user_prompt)},
    ]
    options = {
        "temperature": temperature
    }

    pprint(payload, width=200)
    print(f"model={model}")
    resp = chat(model, messages=payload, options=options)
    answer = resp.message.content.strip().lower()
    print("-" * 100)
    pprint(answer, width=200)

    # Remove <think> from qwen output
    answer = re.sub(r"<think>.*?</think>", "", answer, flags=re.DOTALL).strip()
    return answer

def _check_response(response: str,
                    system: System,
                    model: str = "qwen3:8b",
                    temperature: float = 0.2,
                    timeout: int = 30,):

    developer_names = ""
    if system:
        names = list(system.current().developer_orgs.values_list('name', flat=True))
        if names:
            developer_names = " and ".join(names)

    system_prompt = (
        "You are a classification and validation model.\n"
        "Your task is to determine whether a given text is summarizing the contents of a webpage about a database system.\n"
        "You must output ONLY one word and no additional text: true or false.\n"
        "true  = the text discusses the database system\n"
        "false = the text does not discuss database system\n\n"
        "You must evaluate whether the text is a summary of:\n"
        "  1. Some technical aspect about the database system, and/or\n"
        "  2. The developer or organization responsible for that database system.\n\n"
        "If the page looks like spam or contains information not related to database systems (e.g., gambling, online education, pornography, crypto), then output false.\n"
        "Do NOT speculate. Base your judgment only on the provided text.\n"
        "Do NOT include explanations or commentary.\n"
    )

    user_prompt = (
        f"Database system: {system.name}\n"
        f"Developer / organization: {developer_names}\n\n"
        "TEXT START:\n"
        f"{response}\n"
        "TEXT END\n\n"
        "Determine whether the text above is summarizing a webpage about the "
        "specified database system and/or its developer."
    )

    answer = _run_prompt(system_prompt, user_prompt, model, temperature)
    if any(fr in answer for fr in FUDGEY_RESPONSES_CORRECT_SUMMARIZE):
        return True
    if answer not in {"true", "false"}:
        raise UnexpectedResponseError(f"Unexpected response check LLM response [model={model} / temperature={temperature}]:\n{answer!r}")

    return answer == "true"
