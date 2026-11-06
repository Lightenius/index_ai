# Kullanıcıdan gelen input değerlendirilecek. Konuşma mı, hesaplama isteği mi, başka bir şey mi belirlenecek.
# Belirlenen tipe göre ya programlar çalıştırılacak ya da llm çalıştırılacak.

import json

from logger import Logger
import platform_calculator
import re
import llm_manager


class InputHandler:
    def __init__(self):
        pass

    def handle_input(self, user_input: str):
        # Determine the type of input and process accordingly
        Logger.msg(user_input)

        if self.is_calculation_request(user_input):
            return self.handle_calculation(user_input)

        return self.handle_conversation(user_input)


    def is_calculation_request(self, user_input: str) -> bool:

        if user_input.count(".calc") > 0 or user_input.count(".compute") > 0 or user_input.count(".hesap") > 0 or user_input.count(".hesapla") > 0:
            Logger.info("Input identified as a calculation request.")
            return True
        else:
            return False
        

    def is_conversation(self, user_input: str) -> bool:
        # Logic to determine if the input is a conversational request
        pass


    def parse_calculation_input(self, user_input: str) -> dict:
        # Extract parameters from the user input for calculation
        # This is a placeholder implementation; you would need to implement actual parsing logic
        prompt = f"""Extract parameters from the following input for a calculation: {user_input}. 
        Return a dictionary with keys: 
        camera_count (default 10), 
        archive_days (default 30), 
        resolution (default 1920x1080, always use axb format for resolution. example: 1920x1080, 1280x720, 640x480), 
        fps (default 25), 
        codec (default H.265). 
        return only the dictionary."""
        
        result = llm_manager.ask_direct_llm(prompt)
        # validate result is a valid dictionary

        try:
            Logger.debug(f"LLM output for parsing calculation input: {result}")

            ###   !!!! DÜZELTİLECEK GEÇİCİ ÇÖZÜM !!!!  ###
            vals = json.loads(result[0:result.find("}")+1])  # This will raise an exception if the result is not a valid JSON
            return vals

        except (json.JSONDecodeError) as e:
            Logger.error(f"Failed to parse LLM output as JSON: {e}")
            # Logger.error("The result from LLM is not a valid dictionary.")
            return None


    def handle_calculation(self, user_input: str):
        # Use the platform_calculator to process the calculation
        parsed_input = self.parse_calculation_input(user_input)
        if parsed_input is None:
            Logger.error("Failed to parse calculation input.")
            Logger.error("Sending error message to user.")
            
            return None
        
        result = platform_calculator.calculate_platform(
            camera_count = parsed_input['camera_count'],
            archive_days = parsed_input['archive_days'],
            resolution = parsed_input['resolution'],
            fps = parsed_input['fps'],
            codec = parsed_input['codec'],
            software = "Axxon One (x64)",
            calculation_type = "Server",
        )
        return result


    def handle_conversation(self, user_input: str):
        # Logic to handle conversational requests
        pass


    def handle_other(self, user_input: str):
        # Logic to handle other types of requests
        pass