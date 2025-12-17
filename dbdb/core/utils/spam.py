import re
from ollama import chat
from pprint import pprint
from dbdb.core.models import System

class UnexpectedResponseError(RuntimeError):
    pass

# Sometimes qwen outputs "**not spam**", so we can just treat that as a valid response
FUNKY_RESPONSES = [
    '**answer:** not spam',
    '**not spam**',
]


def is_spam(
    html: str,
    system: System,
    *,
    model: str = "qwen3:8b", # "llama3.2",
    temperature: float = 0.2,
    # ollama_url: str = "http://localhost:11434/api/chat",
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
        "Your task is to decide whether a web page has been taken over by spam.\n\n"
        "A page is SPAM if it primarily contains content such as:\n"
        "- Online gambling or betting\n"
        "- Pornography or adult services\n"
        "- Online pharmacies or prescription drug sales\n"
        "- Crypto or financial scams\n"
        "- SEO spam, link farms, or auto-generated keyword pages\n"
        "- Domain parking pages (GoDaddy) or ads with no substantive content\n\n"
        "The page is NOT spam if it primarily discusses technical, educational, or "
        "documentation-related information about the expected topic. "
        "If the page contains source code, then you assume it is for the database system and is not spam. "
        "Do not try to summarize or explain any code.\n\n"
        "Ignore HTML tags, navigation menus, cookie banners, and generic ads.\n"
        "Focus on the semantic intent and dominant topic of the page.\n\n"
        "You must output ONLY one word: true or false.\n"
        "true  = the page is spam\n"
        "false = the page is not spam"
    )

    user_prompt = [ ]
    first_line = ""
    if system:
        # Add the system name and the developers (if they exist).
        # Adding the developer is useful for when pages talk about a company acquisition
        # but the name of the company is not the same as the database system (e.g., RedHat's etcd).
        first_line = f"The expected topic of this page is the database system '{system.name}'"
        developer = system.current().developer
        if developer:
            first_line += f" and/or {system.name}'s developers " + " and ".join(map(str.strip, developer.split(",")))
    else:
        first_line = f"The expected topic of this page is about database systems"
    user_prompt = [
        f"{first_line}.\n\n"
        "Determine whether the following HTML page has been taken over by spam, "
        "rather than legitimately discussing this database system.\n\n"
        "HTML CONTENT START\n"
        f"{html[:12000]}\n"
        "HTML CONTENT END\n\n"
        "Answer:"
    ]
    print(f"Invoking '{model}' run spam checker [system={system}]")

    payload = [
            {"role": "system", "content": "".join(system_prompt)},
            {"role": "user", "content": "".join(user_prompt)},
    ]
    options = {
        "temperature": temperature
    }

    pprint(payload, width=200)
    resp = chat(model, messages=payload, options=options)
    answer = resp.message.content.strip().lower()
    print("-"*100)
    pprint(answer, width=200)

    # Remove <think> from qwen output
    answer = re.sub(r"<think>.*?</think>", "", answer, flags=re.DOTALL).strip()

    if any(fr in answer for fr in FUNKY_RESPONSES):
        return False

    if answer not in {"true", "false"}:
        raise UnexpectedResponseError(f"Unexpected LLM response [temperature={temperature}]:\n{answer!r}")

    return answer == "true"
