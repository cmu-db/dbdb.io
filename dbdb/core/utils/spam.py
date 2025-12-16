from ollama import chat

from pprint import pprint

def is_spam(
    html: str,
    database_name: str,
    *,
    model: str = "llama3.2",
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
        "documentation-related information about the expected topic.\n\n"
        "Ignore HTML tags, navigation menus, cookie banners, and generic ads.\n"
        "Focus on the semantic intent and dominant topic of the page.\n\n"
        "You must output ONLY one word: true or false.\n"
        "true  = the page is spam\n"
        "false = the page is not spam"
    )

    user_prompt = [ ]

    if database_name:
        user_prompt.append(f"The expected topic of this page is the database system '{database_name}'.")
    else:
        user_prompt.append(f"The expected topic of this page is about database systems.")
    user_prompt[0] += "\n\n"
    user_prompt += [
        "Determine whether the following HTML page has been taken over by spam, "
        "rather than legitimately discussing this database system.\n\n"
        "HTML CONTENT START\n"
        f"{html[:15000]}\n"
        "HTML CONTENT END\n\n"
        "Answer:"
    ]
    print(f"Invoking '{model}' run spam checker [system={database_name}]")

    payload = [
            {"role": "system", "content": "".join(system_prompt)},
            {"role": "user", "content": "".join(user_prompt)},
    ]
    pprint(payload, width=200)
    resp = chat(model, messages=payload)
    answer = resp.message.content.strip().lower()
    print("-"*100)
    pprint(answer, width=200)

    if answer not in {"true", "false"}:
        raise ValueError(f"Unexpected LLM response: {answer!r}")

    return answer == "true"
