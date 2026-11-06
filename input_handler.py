# Kullanıcıdan gelen input değerlendirilecek. Konuşma mı, hesaplama isteği mi, başka bir şey mi belirlenecek.
# Belirlenen tipe göre ya programlar çalıştırılacak ya da llm çalıştırılacak.


import re


class InputHandler:
    def __init__(self):
        pass

    def handle_input(self, user_input: str):
        # Determine the type of input and process accordingly
        if self.is_calculation_request(user_input):
            return self.handle_calculation(user_input)

        return self.handle_conversation(user_input)


    def is_calculation_request(self, user_input: str) -> bool:

        if re.search(r'\b(\.calc|\.compute|\.hesap|\.hesapla)\b', user_input, re.IGNORECASE):
            return True
        else:
            return False
        

    def is_conversation(self, user_input: str) -> bool:
        # Logic to determine if the input is a conversational request
        pass


    def handle_calculation(self, user_input: str):
        # Logic to handle calculation requests
        pass


    def handle_conversation(self, user_input: str):
        # Logic to handle conversational requests
        pass


    def handle_other(self, user_input: str):
        # Logic to handle other types of requests
        pass