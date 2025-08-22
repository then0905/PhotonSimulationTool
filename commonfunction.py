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
    
    def load_skill_icon(job:str,skillId:str):
        """
        讀取技能Icon資源
        """
        return CommonFunction.load_image_resource(f'skill_icon/Icon/{job}',skillId)
    
    def load_status_effect_icon(effectId:str):
        """
        讀取效果Icon資源
        """
        return CommonFunction.load_image_resource(f'status_effect_icon/',effectId)

    def load_image_resource(path,name):
        """
        依照路徑與名稱獲取圖片資源
        """
        import tkinter as tk
        icon = tk.PhotoImage(file=f"{path}/{name}.png")  # PNG 圖片
        return icon



