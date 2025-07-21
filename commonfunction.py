from game_models import GameData


class CommonFunction:
    @staticmethod
    def get_text(text_id: str) -> str:
        """
        從GameText取得文字內容
        
        Args:
            text_id: 文字ID
        """
        text_obj = GameData.Instance.GameTextDataDic.get(text_id, None)
        if text_obj is not None:
            return text_obj.TextContent
        return f"[{text_id}]"

    def clamp(value, min_value, max_value):
        """
         控制一個數的範圍不超過最小值與最大值
        """
        return max(min_value, min(value, max_value))



