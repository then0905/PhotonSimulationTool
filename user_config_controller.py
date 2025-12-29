from dataclasses import dataclass

@dataclass
class UserConfigController:
    def __init__(self, model, app):
        self.model = model
        self.view = app
        # 1. 啟動時：從本地讀取資料 -> 更新 UI
        self.load_config_to_view()

    def load_config_to_view(self):
        """將 Model 資料注入 View 的變數"""
        data = self.model.load()  # 取得 dict 資料

        for key, value in data.items():
            # 如果這個 key 在 View 裡面有被註冊過，就更新它
            if key in self.view.vars_registry:
                # 注意：Tkinter 變數更新會自動刷新 UI
                self.view.vars_registry[key].set(value)

        #主介面運行後預設跑一次 讓敵人的UI正確依設定開關
        self.view.update_enemy_ui_by_type()

        print(f"配置已載入: {data}")

    def save_view_to_config(self):
        """從 View 收集資料存回 Model"""
        data_to_save = {}

        for key, var in self.view.vars_registry.items():
            # 取得目前 UI 上的值
            data_to_save[key] = var.get()

        self.model.save(data_to_save)
        print("配置已儲存至本地")