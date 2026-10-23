# loads json files to dicts
# can save dict lists to json files
# handles chats, chat history, and documents

import datetime
import json
import file_manager



def load_json_file(file_path: str) -> list[list[dict]]:
    """
    JSON dosyasını yükler ve bir liste döndürür.

    Args:
        file_path (str): Yüklenecek JSON dosyasının yolu.

    Returns:
        list[list[dict]]: JSON dosyasındaki verileri içeren liste.
    """
    
    bytes_json = bytes()

    try:
        bytes_json = file_manager.load_file(file_path)
    except FileNotFoundError:
        return []

    json_content = json.loads(bytes_json)

    return json_content


    

class chat:

    chat_data = []
    # Chat data is structured as list[list[dict{sender, date, content}]]
    # First message in a chat is always from the user and it is the name of the chat 


    @staticmethod
    def get_chat_name(chat_id: int) -> str:
        if chat.chat_data == []:
            return "No chats available"
        return chat.chat_data[chat_id][0]['content'][0:22] + "..." if 0 <= chat_id < len(chat.chat_data) else "Invalid chat ID"

    
    @staticmethod
    def get_chat(chat_id: int) -> list[dict]:
        if chat.chat_data == []:
            return []
        return chat.chat_data[chat_id] if 0 <= chat_id < len(chat.chat_data) else []


    @staticmethod
    def load_chat_data():
        chat.chat_data = load_json_file("data/chats.json")


    @staticmethod
    def save_chat_data():
        data =json.dumps(chat.chat_data, indent=4)
        file_manager.create_file("data/chats.json", data.encode('utf-8'))



    @staticmethod
    def add_message(chat_id: int, sender: str, content: str):
        if chat.chat_data == []:
            chat.chat_data = [[]]
        if 0 <= chat_id < len(chat.chat_data):
            chat.chat_data[chat_id].append({
                "sender": sender,
                "date": str(datetime.datetime.now()), 
                "content": content
            })
        else:
            raise ValueError("Invalid chat ID")

        
class document:
    
    @staticmethod
    def get_document_list():
        return



chat.load_chat_data()
chat.add_message(0, "tester", "Hello, this is a test message.")
print(chat.get_chat(0))
print()
print(chat.chat_data, flush=True)
chat.save_chat_data()