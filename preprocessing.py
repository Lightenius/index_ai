# Eğer input handler bir girdinin llm'e gitmesine karar verdiyse bu katmanda bu girdi üzerinde işlemler yapılacak.

def preprocess_input(user_input: str) -> str:
    # Implement any preprocessing steps needed for the input before sending to LLM
    # For example, you might want to clean up whitespace, remove special characters, etc.
    processed_input = user_input.strip()
    return processed_input

