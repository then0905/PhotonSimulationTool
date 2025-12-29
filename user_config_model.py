import json
import os

class UserConfigModel:
    def __init__(self, filepath="config.json"):
        self.filepath = filepath
        # 這裡是預設配置 (資料結構)
        self.default_config = {
            "player_name": "玩家1",
            "player_race_var": "Human",
            "player_class_var": "",
            "player_level_var": 1,

            "monster_var": "",
            "enemy_race_var": "Human",
            "enemy_class_var": "",
            "enemy_level_var": 1,
            "enemy_type_var": "monster",

        }
        self.current_config = self.default_config.copy()

    def load(self):
        """讀取本地配置，若無檔案則回傳預設值"""
        if not os.path.exists(self.filepath):
            return self.default_config

        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                saved_data = json.load(f)
                # 合併儲存的資料與預設值 (避免舊存檔缺新欄位報錯)
                data = self.default_config.copy()
                data.update(saved_data)
                self.current_config = data
                return data
        except Exception as e:
            print(f"讀取錯誤: {e}")
            return self.default_config

    def save(self, data):
        """將資料寫入本地"""
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            self.current_config = data
        except Exception as e:
            print(f"存檔錯誤: {e}")