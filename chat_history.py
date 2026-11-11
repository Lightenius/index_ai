import datetime
from typing import Dict, List

class ChatHistory:
    h: Dict[int, List[str]] = {}

    @staticmethod
    def reset():
        ChatHistory.h = {}

    @staticmethod
    def saveHistory():
        filepath = f"logs/chat_log_{datetime.datetime.now():%Y%m%d_%H%M%S}.log"

        f = open(filepath, "w", encoding="utf8")
        for k in ChatHistory.h.keys():
            f.write(f"ChatID: {k}\nChat Content: \n")
            for i, msg in  enumerate(ChatHistory.h[k]):
                f.write(f"\t{i}:\t{msg}\n")
            f.write("\n\n==================================================\n\n")
        f.close()