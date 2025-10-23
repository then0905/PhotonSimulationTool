﻿from game_models import GameData


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
    
    def load_item_icon(itemId):
        """
        讀取道具Icon資源
        """
        return CommonFunction.load_image_resource(f'item_icon/',itemId)

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

    def battlelog_text_processor(input_log_dic,log_type:str,other = None):
        """
        取得戰鬥Log 文字樣式 
        """
        log_dic = {
                "caster_text":input_log_dic.get("caster_text",""),
                "caster_color":input_log_dic.get("caster_color","#ff0000"),
                "caster_size":input_log_dic.get("caster_size", 10),
                "descript_text":input_log_dic.get("descript_text",""),
                "descript_color":input_log_dic.get("descript_color","#ff0000"),
                "descript_size":input_log_dic.get("descript_size", 10),
                "target_text":input_log_dic.get("target_text", ""),
                "target_color":input_log_dic.get("target_color", "#ff0000"),
                "target_size":input_log_dic.get("target_size", 0)
        }
        
        match(log_type):
            case "miss":
                return (f'<size={log_dic["caster_size"]}><color={log_dic["caster_color"]}>{log_dic["caster_text"]}</color></size>' 
                f' 使用 <size={log_dic["descript_size"]}><color={log_dic["descript_color"]}>{log_dic["descript_text"]}</color></size>'
                f'但攻擊並沒有命中！')
            case "block":
                return (f'<size={log_dic["caster_size"]}><color={log_dic["caster_color"]}>{log_dic["caster_text"]}</color></size>' 
                f' 使用 <size={log_dic["descript_size"]}><color={log_dic["descript_color"]}>{log_dic["descript_text"]}</color></size>'
                f'但被格檔了！')
            case "damage":
                 return (f'<size={log_dic["caster_size"]}><color={log_dic["caster_color"]}>{log_dic["caster_text"]}</color></size>' 
                f' 使用 <size={log_dic["descript_size"]}><color={log_dic["descript_color"]}>{log_dic["descript_text"]}</color></size>'
                f' 對 <size={log_dic["target_size"]}><color={log_dic["target_color"]}>{log_dic["target_text"]}</color></size>'
                f'造成 {other} 傷害！')
            case "normalAttckTimer":
                return (f'[<size={log_dic["caster_size"]}><color={log_dic["caster_color"]}>{log_dic["caster_text"]}</color></size>' 
                f' 進入 <size={log_dic["descript_size"]}><color={log_dic["descript_color"]}>{log_dic["descript_text"]}</color></size> 計時'
                f' {other} 秒 ]{'\n'}')
            case "skillTimer":
                 return (f'[<size={log_dic["caster_size"]}><color={log_dic["caster_color"]}>{log_dic["caster_text"]}</color></size>' 
                f' 施放了 <size={log_dic["descript_size"]}><color={log_dic["descript_color"]}>{log_dic["descript_text"]}</color></size> 需等待'
                f' {other} 秒 ]{'\n'}')
            case "effectRecovery":
                return (f'<size={log_dic["caster_size"]}><color={log_dic["caster_color"]}>{log_dic["caster_text"]}</color></size>' 
                f' 使用 <size={log_dic["descript_size"]}><color={log_dic["descript_color"]}>{log_dic["descript_text"]}</color></size>'
                f' 對 <size={log_dic["target_size"]}><color={log_dic["target_color"]}>{log_dic["target_text"]}</color></size>'
                f'恢復 {other}')
            case "naturalHpRecovery":
                return (f'自然回復生命 讓<size={log_dic["caster_size"]}><color={log_dic["caster_color"]}>{log_dic["caster_text"]}</color></size>' 
                f' 恢復了 [ <size={log_dic["descript_size"]}><color={log_dic["descript_color"]}>{log_dic["descript_text"]} 生命 ]</color></size>{'\n'}')
            case "naturalMpRecovery":
                return (f'自然回復魔力 讓<size={log_dic["caster_size"]}><color={log_dic["caster_color"]}>{log_dic["caster_text"]}</color></size>' 
                f' 恢復了 [ <size={log_dic["descript_size"]}><color={log_dic["descript_color"]}>{log_dic["descript_text"]} 魔力 ]</color></size>{'\n'}')
            case "continuanceBuff":
                return (f'<size={log_dic["caster_size"]}><color={log_dic["caster_color"]}>{log_dic["caster_text"]}</color></size>' 
                f' 對 <size={log_dic["target_size"]}><color={log_dic["target_color"]}>{log_dic["target_text"]}</color></size>'
                f' 使用 Buff：<size={log_dic["descript_size"]}><color={log_dic["descript_color"]}>{log_dic["descript_text"]}</color></size>'
                f' 持續 {other} 秒')
            case "passiveBuff":
                return (f'<size={log_dic["caster_size"]}><color={log_dic["caster_color"]}>{log_dic["caster_text"]}</color></size>' 
                f' 對 <size={log_dic["target_size"]}><color={log_dic["target_color"]}>{log_dic["target_text"]}</color></size>'
                f' 啟動 被動技能：<size={log_dic["descript_size"]}><color={log_dic["descript_color"]}>{log_dic["descript_text"]}</color></size>')
            case "additiveBuff":
                return (f'<size={log_dic["caster_size"]}><color={log_dic["caster_color"]}>{log_dic["caster_text"]}</color></size>' 
                f' 對 <size={log_dic["target_size"]}><color={log_dic["target_color"]}>{log_dic["target_text"]}</color></size>'
                f' 施加 疊加性效果：<size={log_dic["descript_size"]}><color={log_dic["descript_color"]}>{log_dic["descript_text"]}</color></size>'
                f' 持續 {other} 秒')
            case "continuanceItem":
                return (f'<size={log_dic["caster_size"]}><color={log_dic["caster_color"]}>{log_dic["caster_text"]}</color></size>' 
                f' 對 <size={log_dic["target_size"]}><color={log_dic["target_color"]}>{log_dic["target_text"]}</color></size>'
                f' 使用道具：<size={log_dic["descript_size"]}><color={log_dic["descript_color"]}>{log_dic["descript_text"]}</color></size>'
                f' 持續 {other} 秒')
            case "crowdControlStart":
                return (f'<size={log_dic["caster_size"]}><color={log_dic["caster_color"]}>{log_dic["caster_text"]}</color></size>' 
                f' 使 <size={log_dic["target_size"]}><color={log_dic["target_color"]}>{log_dic["target_text"]}</color></size>'
                f' 進入 {other} 秒的'
                f'<size={log_dic["descript_size"]}><color={log_dic["descript_color"]}>{log_dic["descript_text"]}</color></size>的控制狀態')
            case "debuffStart":
                return (f'<size={log_dic["caster_size"]}><color={log_dic["caster_color"]}>{log_dic["caster_text"]}</color></size>' 
                f' 使 <size={log_dic["target_size"]}><color={log_dic["target_color"]}>{log_dic["target_text"]}</color></size>'
                f' 進入 {other} 秒的'
                f'<size={log_dic["descript_size"]}><color={log_dic["descript_color"]}>{log_dic["descript_text"]}</color></size>的負面狀態')
            case "crowdControlEnd":
                return (f'<size={log_dic["caster_size"]}><color={log_dic["caster_color"]}>{log_dic["caster_text"]}</color></size>' 
                f' 解除了 <size={log_dic["descript_size"]}><color={log_dic["descript_color"]}>{log_dic["descript_text"]}</color></size> 的控制狀態')
            case "debuffEnd":
                return (f'<size={log_dic["caster_size"]}><color={log_dic["caster_color"]}>{log_dic["caster_text"]}</color></size>' 
                f' 解除了 <size={log_dic["descript_size"]}><color={log_dic["descript_color"]}>{log_dic["descript_text"]}</color></size> 的負面狀態')