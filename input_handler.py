# Kullanıcıdan gelen input değerlendirilecek. Konuşma mı, hesaplama isteği mi, başka bir şey mi belirlenecek.
# Belirlenen tipe göre ya programlar çalıştırılacak ya da llm çalıştırılacak.

import json

import axxonParser
import embedding
from logger import Logger
import platform_calculator
import re
import llm_manager
from chat_history import ChatHistory


DEFAULT_XML_DIR = "./xml_output/"


class InputHandler:
    def __init__(self):
        pass

    async def handle_input(self, user_input: str, chat_id: int):
        # Determine the type of input and process accordingly
        Logger.msg(user_input)

        if self.is_calculation_request(user_input):
            return await self.handle_calculation(user_input)

        return await self.handle_conversation(user_input, chat_id=chat_id)


    def is_calculation_request(self, user_input: str) -> bool:
        if user_input.count(".calc") > 0 or user_input.count(".compute") > 0 or user_input.count(".hesap") > 0 or user_input.count(".hesapla") > 0:
            Logger.info("Input identified as a calculation request.")
            return True
        else:
            return False


    def is_save_calculation(self, user_input):
        if user_input.count(".save") != 0 or user_input.count(".kaydet") != 0:
            Logger.info("XLS files will be saved after calculation")
            return True
        else:
            return False


    def is_conversation(self, user_input: str) -> bool:
        pass
        


    async def parse_calculation_input(self, user_input: str) -> dict:
        # Extract parameters from the user input for calculation
        # This is a placeholder implementation; you would need to implement actual parsing logic
        prompt = f"""Extract parameters from the following input for a calculation: {user_input}. 
        Return a dictionary with keys: 
        camera_count (default 10), 
        archive_days (default 30), 
        resolution (default 1920x1080, always use axb format for resolution. all valid options are as follows: '200x100', '320x240', '400x200', '352x288', '704x288', '640x360', '640x480', '704x480', '704x576', '720x576', '800x600', '1024x768', '1280x720', '1280x960', '1280x1024', '1600x1200', '1920x1080', '2048x1536', '3012x1152', '2560x1440', '2688x1520', '2560x1600', '2048x2048', '2560x1920', '2592x1920', '2592x1944', '2560x2048', '3072x1728', '3072x2048', '2560x2560', '3072x2304', '6400x1200', '3840x2160', '4096x2160', '3072x3072', '3648x2752', '4000x3000', '4000x3072', '5472x3648', '7680x4320', '8192x4320'), 
        fps (default 25; example(value): 12 f (12), 25 (25), 30 fp (30), 60 fps (60), 80 kare (80)), 
        codec (default H.264, you are allowed to use: H264, H265, MjPEG). 
        recording_percentage=100 (default 100;; genellikle "kayıt %100(100), 35 kayıt(35), %23 (23), tüm gün kayıt yapılacak (100), günün yarısında kayıt yapılacak (50), kısmi kayıt yapılacak (70) şeklinde bilgi gelebilir.),
        return only the dictionary."""
        
        result = await llm_manager.ask_direct_llm_async(prompt, llm_name="qwen3:4b")
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


    async def handle_calculation(self, user_input: str):
        # Use the platform_calculator to process the calculation
        parsed_input = await self.parse_calculation_input(user_input)
        if parsed_input is None:
            Logger.error("Failed to parse calculation input.")
            Logger.error("Sending error message to user.")
            
            return None

        XML_path = None if not self.is_save_calculation(user_input=user_input) else DEFAULT_XML_DIR
        
        
        platform_result = await platform_calculator.calculate_platform(
            camera_count=parsed_input.get("camera_count", 10),
            archive_days=parsed_input.get("archive_days", 30),
            resolution=parsed_input.get("resolution", "1920x1080"),
            fps=parsed_input.get("fps", 25),
            codec=parsed_input.get("codec", "H.265"),
            recording_percentage=parsed_input.get("recording_percentage", 50),
            save_xls_to = XML_path
        )

        llm_response = await llm_manager.ask_direct_llm_async(
            f"""User requested a calculation with the following parameters: {parsed_input}. 
        The platform calculator returned: {platform_result}. 
        Please provide a user-friendly summary of the results.
        Make it very short, not more than 2 paragraphs.
        At the start, clearly show each input in a 
        key -> value,
        key -> value,
        ...
        format.        
        after that , clearly show each result in a 
        key -> value,
        key -> value,
        ...
        format.
        Briefly explain the correlation

        Use Turkish Language.
        """,
            llm_name="qwen3:4b",
            benchmark=False,
        )
        return llm_response


    async def handle_conversation(self, user_input: str, chat_id: int) -> str:

        prev_messages = "{role: system / msg_history \n content: "
        msgs = ChatHistory.h.get(chat_id)
        if msgs is None:
            Logger.warning("Message history not found")
            msgs = []
        to_be_added = []
        if len(msgs) > 10:
            to_be_added = msgs[len(msgs)-10:len(msgs)]
        elif msgs is not None:
            to_be_added = msgs

        prev_messages += "\n".join(to_be_added)
        prev_messages += "}"

        doc_data = ""
        if user_input.count(".doc") != 0:
            pagenums = embedding.query(user_input, 5)
            pages = axxonParser.get_pages("data/raw_manual.pdf")
            for pagenum in pagenums:
                doc_data+= ", {" + f"page_number = {pagenum+1}\npage content = {pages[pagenum]["content"]}" + "} "
                

        system_message = """
        {
            "role": "system"
            "content": "
            Answer in Turkish.
            Boş yapma.
            Kısa ve net konuş.
            Kullanıcıya Patron şeklinde hitap et.
            "
        }
"""
        prompt = "\n\n---\n\n".join([system_message, prev_messages, "{\"role\":\"user\", \"content\":\"" + user_input + "\"\n}", doc_data])
        
        llm_response = await llm_manager.ask_direct_llm_async(
            prompt,
        )
        return llm_response


    def handle_other(self, user_input: str):
        # Logic to handle other types of requests
        pass