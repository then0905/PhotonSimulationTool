import json
import os

class UserConfigModel:
    def __init__(self, app_name="MySimulator"):
        # 取得 AppData/Roaming 路徑
        appdata = os.getenv('APPDATA')
        self.config_dir = os.path.join(appdata, app_name)
        self.filepath = os.path.join(self.config_dir, "user_config.json")

        # 確保資料夾存在
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)

        # 這裡是預設配置 (資料結構)
        self.default_config = {
            "player_name": "玩家1",
            "player_race_var": "Human",
            "player_class_var": "",
            "player_level_var": 1,
            "player_mainhandweapon_id": "",
            "player_mainhandweapon_forge_lv": 0,
            "player_offhandweapon_id": "",
            "player_offhandweapon_forge_lv": 0,
            "player_armor_id_0": "",
            "player_armor_forge_lv_0": 0,
            "player_armor_id_1": "",
            "player_armor_forge_lv_1": 0,
            "player_armor_id_2": "",
            "player_armor_forge_lv_2": 0,
            "player_armor_id_3": "",
            "player_armor_forge_lv_3": 0,
            "player_armor_id_4": "",
            "player_armor_forge_lv_4": 0,

            "monster_var": "",
            "enemy_race_var": "Human",
            "enemy_class_var": "",
            "enemy_level_var": 1,
            "enemy_type_var": "monster",
            "enemy_mainhandweapon_id": "",
            "enemy_mainhandweapon_forge_lv": 0,
            "enemy_offhandweapon_id": "",
            "enemy_offhandweapon_forge_lv": 0,
            "enemy_armor_id_0": "",
            "enemy_armor_forge_lv_0": 0,
            "enemy_armor_id_1": "",
            "enemy_armor_forge_lv_1": 0,
            "enemy_armor_id_2": "",
            "enemy_armor_forge_lv_2": 0,
            "enemy_armor_id_3": "",
            "enemy_armor_forge_lv_3": 0,
            "enemy_armor_id_4": "",
            "enemy_armor_forge_lv_4": 0,

            "fast_skip_var": False,
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