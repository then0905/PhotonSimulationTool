# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox, font
from game_models import GameData, ItemDataModel, ItemEffectData, SkillData
from battle_simulator import BattleSimulator, BattleCharacter
from stats_analyzer import StatsAnalyzer
from status_operation import CharacterStatusCalculator, StatusValues
from commonfunction import CommonFunction
from user_config_controller import UserConfigController
from user_config_model import UserConfigModel
from typing import Dict
from dataclasses import asdict
import os
import re
import traceback


class BattleSimulatorGUI:
    jobNameDict: Dict[str, str] = {}
    monsterNameDict: Dict[str, str] = {}

    def __init__(self, root, model):
        self.root = root
        self.model = model
        self.root.title("UnityAI")

        # 根據螢幕解析度設定視窗大小
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        win_w = int(screen_w * 0.43)
        win_h = int(screen_h * 0.9)

        # 計算縮放比例（以 1440x810 為基準）
        self.scale_x = win_w / 1440
        self.scale_y = win_h / 810
        self.scale = min(self.scale_x, self.scale_y)

        # 設定視窗大小和位置（置中）
        pos_x = (screen_w - win_w) // 2
        pos_y = (screen_h - win_h) // 2
        self.root.geometry(f"{win_w}x{win_h}+{pos_x}+{pos_y}")
        self.root.resizable(True, True)

        # 設定最小視窗大小
        min_w = int(screen_w * 0.43)
        min_h = int(screen_h * 0.9)
        self.root.minsize(min_w, min_h)

        # 加載遊戲數據
        self.game_data = GameData()

        # 用來儲存所有 UI 變數的字典
        self.vars_registry = {}

        # 創建界面
        self.create_widgets()

        # 初始化變量
        self.player_character = None
        self.enemy_character = None
        self.battle_results = []

        self.player_frame
        self.enemy_frame
        self.main_frame

        self.last_battle_data = {}

    def create_var(self, key, var_type, default=None):
        """
        【工廠方法】
        建立 Tkinter 變數並自動註冊到 registry。
        key: 對應 Model (JSON) 裡的 key
        var_type: tk.StringVar, tk.IntVar, tk.BooleanVar
        """
        var = var_type()
        if default is not None:
            var.set(default)

        # 註冊進字典
        self.vars_registry[key] = var
        return var

    def scaled(self, value):
        """根據縮放比例調整數值"""
        return int(value * self.scale)

    def scaled_font(self, size):
        """根據縮放比例調整字體大小"""
        return max(8, int(size * self.scale))

    def create_widgets(self):
        # 主框架
        self.main_frame = ttk.Frame(self.root, padding="0")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        class ColoredBar(tk.Canvas):
            """
            彩色條
            """

            def __init__(self, master, width=200, height=20, fg_color="red", gui_ref=None, **kwargs):
                # 使用縮放後的尺寸
                if gui_ref:
                    width = gui_ref.scaled(width)*1.5
                    height = gui_ref.scaled(height)*1.5

                super().__init__(
                    master,
                    width=width,
                    height=height,
                    bg="gray20",
                    highlightthickness=0,
                    **kwargs,
                )
                self.width = width
                self.height = height
                self.fg_color = fg_color
                self.current_value = 0
                self.max_value = 100
                self.gui_ref = gui_ref
                self.draw_bar()

            def set_value(self, current, max_value):
                """
                設定bar的數值

                 Args:
                    current: 當前值
                    max_value: 最大值
                """
                self.current_value = max(0, min(current, max_value))
                self.max_value = max_value
                self.draw_bar()

            def draw_bar(self):
                """
                繪畫bar的顏色、樣子
                """
                self.delete("all")
                ratio = self.current_value / self.max_value if self.max_value > 0 else 0
                bar_width = int(self.width * ratio)
                self.create_rectangle(
                    0, 0, bar_width, self.height, fill=self.fg_color, outline=""
                )
                self.create_text(
                    self.width // 2,
                    self.height // 2,
                    text=f"{self.current_value}/{self.max_value}",
                    fill="white",
                    font=("Arial", self.gui_ref.scaled_font(10*1.5) if self.gui_ref else 10, "bold"),
                )

        class StatusEffectBar(ttk.Frame):
            def __init__(self, master, gui_ref=None):
                super().__init__(master)
                self.gui_ref = gui_ref

                # 建立 Canvas + Scrollbar 容器
                self.canvas = tk.Canvas(self, height=gui_ref.scaled(48*1.65) if gui_ref else 48)
                self.scrollbar = ttk.Scrollbar(
                    self, orient="horizontal", command=self.canvas.xview
                )

                self.inner_frame = ttk.Frame(self.canvas)

                self.inner_frame.bind(
                    "<Configure>",
                    lambda e: self.canvas.configure(
                        scrollregion=self.canvas.bbox("all")),
                )
                self.canvas.create_window(
                    (0, 0), window=self.inner_frame, anchor="nw")
                self.canvas.configure(xscrollcommand=self.scrollbar.set)

                self.canvas.pack(side="top", fill="x", expand=True)
                self.scrollbar.pack(side="bottom", fill="x")

                self.effects = []  # 儲存技能效果UI與資料
                self.popup = None  # 暫時視窗參考

                # 綁定全域點擊事件關閉 popup
                self.canvas.bind_all("<Button-1>", self._on_global_click, "+")

            def _is_descendant(self, widget, parent):
                """判斷 widget 是否為 parent 的子孫"""
                while widget is not None:
                    if widget is parent:
                        return True
                    widget = getattr(widget, "master", None)
                return False

            def _create_effect_widget(self, icon, name, desc, effect_id, stack_count=0):
                """
                icon: Tkinter.PhotoImage
                name: 顯示名稱
                desc: 說明文字
                effect_id: 效果 ID
                stack_count: 疊層數字（0 表示不顯示）
                """
                # 自動依比例縮小圖示到最大 55x55
                max_size = self.gui_ref.scaled(48*1.65) if self.gui_ref else 48
                width = icon.width()
                height = icon.height()
                scale_factor = max(width / max_size, height / max_size, 1)
                new_width = int(width / scale_factor)
                new_height = int(height / scale_factor)
                icon = icon.subsample(max(int(width / new_width), 1), max(int(height / new_height), 1))

                # 建立 Canvas 放圖示
                c = tk.Canvas(self.inner_frame, width=max_size, height=max_size, highlightthickness=0, bg="white")
                c.create_image(0, 0, anchor="nw", image=icon)

                # 疊加數字 (右下角) → 只有 stack_count > 0 才顯示
                if stack_count > 0:
                    c.create_text(
                        max_size - 5, max_size - 5,
                        text=str(stack_count),
                        fill="black",
                        font=("Arial", self.gui_ref.scaled_font(10*1.65) if self.gui_ref else 10, "bold")
                    )

                # 綁定點擊事件（顯示 popup）
                c.bind("<Button-1>", lambda e, n=name, d=desc: self._show_popup(e, n, d))

                # 放入欄位
                c.pack(side="left", padx=self.gui_ref.scaled(2*1.65) if self.gui_ref else 2)

                # 保存資訊
                self.effects.append({
                    "id": effect_id,
                    "name": name,
                    "desc": desc,
                    "widget": c,
                    "icon": icon,
                    "stack": stack_count
                })

            def add_skill_effect(self, id: str, skill, stack_count=0):
                """
                增加技能效果提示物件
                """

                # 疊層類型先判斷是否已存在
                if (stack_count > 0):
                    for eff in self.effects:
                        if eff["id"] == id:
                            eff["stack"] = CommonFunction.clamp(eff["stack"] + stack_count, 0,
                                                                int(skill.SkillOperationDataList[0].Bonus[0]))
                            # --- 更新 Canvas 數字 ---
                            c = eff["widget"]
                            c.delete("stack_text")  # 刪除舊的數字
                            if eff["stack"] > 0:
                                max_size = self.gui_ref.scaled(48*1.65) if self.gui_ref else 48
                                c.create_text(
                                    max_size - 5,
                                    max_size - 5,
                                    text=str(eff["stack"]),
                                    fill="black",
                                    font=("Arial", self.gui_ref.scaled_font(10*1.65) if self.gui_ref else 10, "bold"),
                                    tags="stack_text",  # 給標籤方便刪除
                                )
                            return

                skillIcon = CommonFunction.load_skill_icon(skill.Job, skill.SkillID)
                if not skillIcon:
                    print("讀取失敗")
                    return
                skillName = CommonFunction.get_text(skill.Name)
                skillIntro = CommonFunction.get_text(skill.Intro) + '\n'
                for op in skill.SkillOperationDataList:
                    if op.InfluenceStatus:
                        skillIntro += f"{CommonFunction.get_text('TM_' + op.InfluenceStatus)} : {CommonFunction.get_text('TM_' + op.AddType).format(op.EffectValue)}\n"
                self._create_effect_widget(skillIcon, skillName, skillIntro, id, stack_count)

            def add_item_effect(self, id: str, item, stack_count=0):
                """
                增加道具效果提示物件
                """

                itemIcon = CommonFunction.load_item_icon(item.CodeID)
                if not itemIcon:
                    print("讀取失敗")
                    return
                itemName = CommonFunction.get_text(item.Name)
                itemIntro = CommonFunction.get_text(item.Intro) + '\n'
                for op in item.ItemEffectDataList:
                    if op.InfluenceStatus:
                        itemIntro += f"{CommonFunction.get_text('TM_' + op.InfluenceStatus)} : {CommonFunction.get_text('TM_' + op.AddType).format(op.EffectValue)}\n"
                self._create_effect_widget(itemIcon, itemName, itemIntro, id, stack_count)

            def add_debuff(self, id: str, effectId, stack_count=0):
                statusEffectIcon = CommonFunction.load_status_effect_icon(effectId)
                if not statusEffectIcon:
                    print("讀取失敗")
                    return
                statusEffectName = CommonFunction.get_text(f"TM_{effectId}_Name")
                statusEffectIntro = CommonFunction.get_text(f"TM_{effectId}_Intro")
                self._create_effect_widget(statusEffectIcon, statusEffectName, statusEffectIntro, id, stack_count)

            def remove_effect(self, id):
                """
                移除一個技能效果圖示
                """
                for eff in self.effects:
                    if eff["id"] == id:
                        eff["widget"].destroy()
                self.effects = [
                    eff for eff in self.effects if eff["id"] != id]

            def get_effect_stack(self, id) -> int:
                """
                取得指定技能當前的疊層
                """
                if (self.effects is not None):
                    for eff in self.effects:
                        if eff["id"] == id or eff["id"].startswith(id):
                            return eff["stack"]
                return 0

            def set_effect_stack(self, id, target_stack):
                """
                設定指定技能當前的疊層
                """
                if (self.effects is not None):
                    for eff in self.effects:
                        if eff["id"] == id or eff["id"].startswith(id):
                            eff["stack"] = target_stack

            def clear_bar(self):
                for eff in self.effects:
                    eff["widget"].destroy()
                self.effects = []

            def _show_popup(self, event, name, description):
                """
                顯示技能說明視窗
                """
                if self.popup:
                    self.popup.destroy()

                self.popup = tk.Toplevel(self)
                self.popup.wm_overrideredirect(True)  # 移除邊框
                self.popup.attributes("-topmost", True)

                # 放在滑鼠旁邊
                x = event.x_root + 10
                y = event.y_root + 10
                self.popup.geometry(f"+{x}+{y}")

                # 顯示內容
                label = ttk.Label(
                    self.popup,
                    text=f"{name}\n\n{description}",
                    background="white",
                    relief="solid",
                    padding=self.gui_ref.scaled(5) if self.gui_ref else 5,
                )
                label.pack()

            def _on_global_click(self, event):
                """
                全域點擊事件：如果點擊的地方不是 popup 或技能按鈕，就關閉 popup
                """
                if not self.popup:
                    return

                w = event.widget

                # 1) 點在 popup 或其子孫 → 不關
                if self._is_descendant(w, self.popup):
                    return

                # 2) 點在任一技能按鈕 → 不關
                for eff in self.effects:
                    if self._is_descendant(w, eff["widget"]):
                        return

                # 3) 其他情況才關
                self.popup.destroy()
                self.popup = None

        class ItemManager:
            def __init__(self, root, prefix, view):
                self.root = root
                self.prefix = prefix
                self.view = view
                # 攜帶的道具資料結構 {item_id: {"count": 數量, "name": 名稱}}
                self.carried_items = {}
                self.view_window = None  # 記錄查看道具視窗

            def open_item_window(self):
                """開啟道具選擇視窗，更新 self.carried_items"""
                item_window = tk.Toplevel(self.root)
                item_window.title("道具選擇")
                item_window.resizable(False, False)

                item_vars = {}
                item_counts = {}

                # 過濾有作用效果的道具
                filtered_items = [
                    item for item in GameData.Instance.ItemsDic.values()
                    if len(item.ItemEffectDataList) > 0
                ]

                current_saved_data = self.view.model.current_config

                # 動態生成道具清單
                for i, item in enumerate(filtered_items):
                    check_key = f"{self.prefix}_item_check_{item.CodeID}"
                    count_key = f"{self.prefix}_item_count_{item.CodeID}"

                    # 1. 嘗試從已讀取的 JSON 資料中抓取，若無則用預設值
                    saved_check = current_saved_data.get(check_key, item.CodeID in self.carried_items)
                    saved_count = current_saved_data.get(count_key,
                                                         self.carried_items.get(item.CodeID, {}).get("count", 1))

                    # 2. 建立變數並給予「來自 JSON」的初始值
                    var = self.view.create_var(check_key, tk.BooleanVar, saved_check)
                    count_var = self.view.create_var(count_key, tk.IntVar, saved_count)

                    item_vars[item.CodeID] = var
                    item_counts[item.CodeID] = count_var

                    ttk.Checkbutton(
                        item_window, text=CommonFunction.get_text(item.Name), variable=var
                    ).grid(row=i, column=0, sticky=tk.W)
                    ttk.Spinbox(
                        item_window, from_=1, to=99, textvariable=count_var, width=5
                    ).grid(row=i, column=1)

                # 點確定更新 carried_items
                def confirm_selection():
                    self.carried_items.clear()
                    for item in filtered_items:
                        if item_vars[item.CodeID].get():
                            self.carried_items[item.CodeID] = {
                                "count": item_counts[item.CodeID].get(),
                                "data": item
                            }
                    item_window.destroy()
                    self.show_current_items()

                ttk.Button(item_window, text="確定", command=confirm_selection).grid(
                    row=len(filtered_items), column=0, columnspan=2, pady=10
                )

            def show_current_items(self):
                if self.view_window and tk.Toplevel.winfo_exists(self.view_window):
                    self.view_window.lift()
                    self.view_window.focus_force()
                    return

                view_window = tk.Toplevel(self.root)
                view_window.title("目前攜帶道具")
                view_window.resizable(False, False)

                self.view_window = view_window

                def on_close():
                    self.view_window.destroy()
                    self.view_window = None

                self.view_window.protocol("WM_DELETE_WINDOW", on_close)

                if not self.carried_items:
                    ttk.Label(view_window, text="沒有攜帶道具").pack(padx=10, pady=5)
                    return

                self.item_labels = {}  # 🔑 存每個 item 的 StringVar
                for i, (item_id, data) in enumerate(self.carried_items.items()):
                    var = tk.StringVar(
                        value=f"{CommonFunction.get_text(data['data'].Name)}: {data['count']}"
                    )
                    self.item_labels[item_id] = var
                    ttk.Label(view_window, textvariable=var).grid(row=i, column=0, padx=10, pady=5)

            def consume_item(self, item_id, amount=1):
                """消耗道具，如果數量歸零就刪除"""
                if item_id not in self.carried_items:
                    print(f"沒有 {item_id} 可以消耗")
                    return False

                current_count = self.carried_items[item_id]["count"]
                if current_count < amount:
                    print(f"{item_id} 數量不足")
                    return False

                self.carried_items[item_id]["count"] -= amount
                if item_id in self.item_labels:
                    if item_id in self.carried_items:
                        self.item_labels[item_id].set(
                            f"{CommonFunction.get_text(self.carried_items[item_id]['data'].Name)}: {self.carried_items[item_id]['count']}"
                        )
                    else:
                        self.item_labels[item_id].set("已消耗完畢")
                return True

        class CharacterOverviewWnd(ttk.Frame):
            """
            角色能力值總覽視窗（可滾動）
            """

            def __init__(self, root):
                super().__init__(root)

                self.root = root
                self.view_window = None
                self.status = {}
                self.status_labels = {}

            def show_overview_wnd(self):
                """開啟能力總覽視窗"""
                if self.view_window and tk.Toplevel.winfo_exists(self.view_window):
                    self.view_window.lift()
                    self.view_window.focus_force()
                    return

                self.view_window = tk.Toplevel(self.root)
                self.view_window.title("能力值總覽")
                self.view_window.resizable(False, False)
                self.view_window.geometry("320x480")

                # 窗口關閉事件
                def on_close():
                    self.view_window.destroy()
                    self.view_window = None

                self.view_window.protocol("WM_DELETE_WINDOW", on_close)

                # ===== Scrollable Canvas =====
                self.canvas = tk.Canvas(self.view_window, bg="#222", highlightthickness=0)
                self.canvas.pack(side="left", fill="both", expand=True)

                self.scrollbar = ttk.Scrollbar(
                    self.view_window, orient="vertical", command=self.canvas.yview
                )
                self.scrollbar.pack(side="right", fill="y")

                self.canvas.configure(yscrollcommand=self.scrollbar.set)

                # 建 inner_frame
                self.inner_frame = ttk.Frame(self.canvas)
                self.canvas_window = self.canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")

                # frame 大小變化時更新 scroll 區域
                self.inner_frame.bind("<Configure>", self._on_frame_configure)

                # canvas 大小變化時同步 frame 寬度
                self.canvas.bind("<Configure>", self._on_canvas_configure)

                # 滑鼠滾輪綁定
                self.canvas.bind("<Enter>", self._bind_mousewheel)
                self.canvas.bind("<Leave>", self._unbind_mousewheel)

                # 初始狀態
                if self.status:
                    self.update_state(self.status)

            ##########################################################
            # Scroll control
            ##########################################################

            def _on_frame_configure(self, event):
                """更新 scroll 區域"""
                self.canvas.configure(scrollregion=self.canvas.bbox("all"))

            def _on_canvas_configure(self, event):
                """讓 inner_frame 寬度自動填滿 canvas"""
                self.canvas.itemconfig(self.canvas_window, width=event.width)

            def _mousewheel(self, event):
                self.canvas.yview_scroll(int(-event.delta / 120), "units")

            def _bind_mousewheel(self, event):
                self.canvas.bind_all("<MouseWheel>", self._mousewheel)

            def _unbind_mousewheel(self, event):
                self.canvas.unbind_all("<MouseWheel>")

            ##########################################################
            # UI 更新
            ##########################################################

            def update_state(self, status: dict):
                """更新能力值 UI"""
                if not self.view_window:
                    return

                self.status = status

                # 清舊 UI
                for widget in self.inner_frame.winfo_children():
                    widget.destroy()

                self.status_labels.clear()

                # 新增 Label
                for i, (key, value) in enumerate(status.items()):
                    label_text = f"{CommonFunction.get_text('TM_' + key)}: {value}"

                    var = tk.StringVar(value=label_text)
                    self.status_labels[key] = var

                    ttk.Label(self.inner_frame, textvariable=var).grid(
                        row=i, column=0, sticky="w", padx=10, pady=4
                    )

        # region 左側玩家設置

        self.player_frame = ttk.LabelFrame(self.main_frame, text="玩家設置", padding="5")
        self.player_frame.grid(row=0, column=0, sticky=tk.N, padx=5, pady=5)

        # 角色名稱
        ttk.Label(self.player_frame, text="角色名稱:").grid(
            row=0, column=0, sticky=tk.W)
        self.player_name = self.create_var("player_name", tk.StringVar, "玩家1")
        ttk.Entry(self.player_frame, textvariable=self.player_name, width=15).grid(
            row=0, column=1
        )

        # 種族選擇
        ttk.Label(self.player_frame, text="種族:").grid(row=1, column=0, sticky=tk.W)
        self.player_race_var = self.create_var("player_race_var", tk.StringVar, "Human")
        player_race_row = ttk.Frame(self.player_frame)
        player_race_row.grid(row=1, column=1, columnspan=3, sticky=tk.W)

        # 不讓子 frame 的欄位去分配多餘空間（避免再次被拉寬）
        for c in range(3):
            player_race_row.grid_columnconfigure(c, weight=0)
        ttk.Radiobutton(
            player_race_row,
            text="人類",
            variable=self.player_race_var,
            value="Human",
            width=6
        ).grid(row=0, column=1, sticky=tk.W)
        ttk.Radiobutton(
            player_race_row,
            text="精靈",
            variable=self.player_race_var,
            value="Elf",
            width=6
        ).grid(row=0, column=2, sticky=tk.W)
        ttk.Radiobutton(
            player_race_row,
            text="德魯伊",
            variable=self.player_race_var,
            value="Druid",
            width=6
        ).grid(row=0, column=3, sticky=tk.W)

        # 職業選擇
        ttk.Label(self.player_frame, text="職業:").grid(row=2, column=0, sticky=tk.W)
        self.player_class_var = self.create_var("player_class_var", tk.StringVar)

        for jobData in GameData.Instance.JobBonusDic.values():
            self.jobNameDict.update(
                {jobData.Job: CommonFunction.get_text("TM_" + jobData.Job)}
            )
        tempJobNameList = list(self.jobNameDict.values())

        ttk.Combobox(
            self.player_frame,
            textvariable=self.player_class_var,
            values=tempJobNameList,
            width=15,
        ).grid(row=2, column=1)
        self.player_class_var.set(next(iter(self.jobNameDict.values())))

        # 角色血量
        self.player_hp_bar = ColoredBar(
            self.player_frame, width=150, height=20, fg_color="red", gui_ref=self
        )
        self.player_hp_bar.grid(row=3, column=1, columnspan=2, pady=2)
        self.player_hp_bar.set_value(100, 100)  # 預設滿血，可根據角色資料初始化

        # 角色魔力
        self.player_mp_bar = ColoredBar(
            self.player_frame, width=150, height=20, fg_color="blue", gui_ref=self
        )
        self.player_mp_bar.grid(row=4, column=1, columnspan=2, pady=2)
        self.player_mp_bar.set_value(50, 50)  # 預設滿魔力，可根據角色資料初始化

        # 等級
        ttk.Label(self.player_frame, text="等級:").grid(row=5, column=0, sticky=tk.W)
        self.player_level_var = self.create_var("player_level_var", tk.IntVar, 1)
        ttk.Spinbox(
            self.player_frame, from_=1, to=100, textvariable=self.player_level_var, width=15
        ).grid(row=5, column=1)
        self.player_level_var.set(1)

        # 左側裝備區
        player_equipment_frame = ttk.LabelFrame(
            self.player_frame, text="裝備欄", padding="3"
        )
        player_equipment_frame.grid(
            row=6, column=0, columnspan=2, padx=1, pady=1, sticky=tk.W
        )
        self.player_equipment_data = self.common_EquipmentUI(
            player_equipment_frame, "player")

        # === 道具按鈕 ===
        # 建立管理器
        self.player_item_manager = ItemManager(player_equipment_frame, "player", self)

        # 按鈕打開道具選擇
        ttk.Button(player_equipment_frame, text="選擇攜帶道具", command=self.player_item_manager.open_item_window).grid(
            row=999, column=0, pady=10)

        # 顯示目前道具
        ttk.Button(player_equipment_frame, text="查看道具", command=self.player_item_manager.show_current_items).grid(
            row=999, column=1, pady=10)

        # === 能力值總覽 ===
        self.player_overview = CharacterOverviewWnd(self.player_frame)
        ttk.Button(self.player_frame, text="能力值總覽", command=self.player_overview.show_overview_wnd).grid(
            row=7, column=1, pady=10)

        # === 狀態效果欄（放裝備欄下方） ===
        self.player_buff_status_bar = StatusEffectBar(self.player_frame, gui_ref=self)
        self.player_buff_status_bar.grid(
            row=8, column=0, columnspan=2, sticky="ew", pady=5)
        self.player_debuff_status_bar = StatusEffectBar(self.player_frame, gui_ref=self)
        self.player_debuff_status_bar.grid(
            row=9, column=0, columnspan=2, sticky="ew", pady=5)
        self.player_passive_status_bar = StatusEffectBar(self.player_frame, gui_ref=self)
        self.player_passive_status_bar.grid(
            row=10, column=0, columnspan=2, sticky="ew", pady=5)

        # endregion

        # region 右側敵人設置
        # ────────────────────────────────
        # 雖然理想的順序是:
        # 敵人類型
        # 選擇怪物
        # 職業
        # 裝備欄
        # 但因為有些需要互相參考 如切換敵人類型 職業跟裝備欄要開關 需要參考到職業裝備的frame
        # 所以UI的建立就沒有照上面的換
        # ────────────────────────────────
        self.enemy_frame = ttk.LabelFrame(self.main_frame, text="敵人設置", padding="5")
        self.enemy_frame.grid(row=0, column=1, sticky="nw", padx=5, pady=5)

        # 怪物選擇

        self.monster_label = ttk.Label(self.enemy_frame, text="選擇怪物:")
        self.monster_label.grid(row=1, column=0, sticky=tk.W)

        self.monster_var = self.create_var("monster_var", tk.StringVar)

        for monsterData in GameData.Instance.MonstersDataDic.values():
            self.monsterNameDict.update(
                {monsterData.MonsterCodeID: CommonFunction.get_text(monsterData.Name)}
            )

        tempMonsterNameList = list(self.monsterNameDict.values())

        self.monster_combobox = (
            ttk.Combobox(
                self.enemy_frame,
                textvariable=self.monster_var,
                values=tempMonsterNameList,
                width=15
            ))
        self.monster_combobox.grid(row=1, column=1, columnspan=1)
        self.monster_var.set(next(iter(self.monsterNameDict.values())))

        # 種族選擇
        self.enemy_race_label = ttk.Label(self.enemy_frame, text="種族:")
        self.enemy_race_label.grid(row=2, column=0, sticky=tk.W)
        self.enemy_race_var = self.create_var("enemy_race_var", tk.StringVar, "Human")
        self.enemy_race_row = ttk.Frame(self.enemy_frame)
        self.enemy_race_row.grid(row=2, column=1, columnspan=3, sticky=tk.W)

        # 不讓子 frame 的欄位去分配多餘空間（避免再次被拉寬）
        for c in range(3):
            self.enemy_race_row.grid_columnconfigure(c, weight=0)
        ttk.Radiobutton(
            self.enemy_race_row,
            text="人類",
            variable=self.enemy_race_var,
            value="Human",
            width=6
        ).grid(row=0, column=1, sticky=tk.W)
        ttk.Radiobutton(
            self.enemy_race_row,
            text="精靈",
            variable=self.enemy_race_var,
            value="Elf",
            width=6
        ).grid(row=0, column=2, sticky=tk.W)
        ttk.Radiobutton(
            self.enemy_race_row,
            text="德魯伊",
            variable=self.enemy_race_var,
            value="Druid",
            width=6
        ).grid(row=0, column=3, sticky=tk.W)

        # 敵對玩家職業
        self.enemy_class_label = ttk.Label(self.enemy_frame, text="職業:")
        self.enemy_class_label.grid(row=3, column=0, sticky=tk.W)
        self.enemy_class_var = self.create_var("enemy_class_var", tk.StringVar)
        for jobData in GameData.Instance.JobBonusDic.values():
            self.jobNameDict.update(
                {jobData.Job: CommonFunction.get_text("TM_" + jobData.Job)}
            )

        tempJobNameList = list(self.jobNameDict.values())
        self.enemy_class_combobox = ttk.Combobox(
            self.enemy_frame,
            textvariable=self.enemy_class_var,
            values=tempJobNameList,
            width=15,
        )
        self.enemy_class_combobox.grid(row=3, column=1)

        self.enemy_class_var.set(next(iter(self.jobNameDict.values())))

        # 敵對玩家等級
        self.enemy_lv_label = ttk.Label(self.enemy_frame, text="等級:")
        self.enemy_lv_label.grid(row=5, column=0, sticky=tk.W)
        self.enemy_level_var = self.create_var("enemy_level_var", tk.IntVar, 1)
        self.enemy_lv_spinbox = ttk.Spinbox(
            self.enemy_frame, from_=1, to=100, textvariable=self.enemy_level_var, width=15
        )
        self.enemy_lv_spinbox.grid(row=5, column=1)

        # 角色血量
        self.enemy_hp_bar = ColoredBar(
            self.enemy_frame, width=150, height=20, fg_color="red", gui_ref=self
        )
        self.enemy_hp_bar.grid(row=6, column=1, columnspan=2, pady=2)
        self.enemy_hp_bar.set_value(100, 100)  # 預設滿血，可根據角色資料初始化
        # 角色魔力
        self.enemy_mp_bar = ColoredBar(
            self.enemy_frame, width=150, height=20, fg_color="blue", gui_ref=self
        )
        self.enemy_mp_bar.grid(row=7, column=1, columnspan=2, pady=2)
        self.enemy_mp_bar.set_value(50, 50)  # 預設滿魔力，可根據角色資料初始化

        # 右側裝備區
        self.enemy_equipment_frame = ttk.LabelFrame(
            self.enemy_frame, text="裝備欄", padding="3")
        self.enemy_equipment_frame.grid(
            row=8, column=0, columnspan=2, padx=1, pady=1, sticky=tk.W
        )
        self.enemy_equipment_data = self.common_EquipmentUI(
            self.enemy_equipment_frame, "enemy")
        # === 道具按鈕 ===
        # 點擊按鈕，先選道具，再開另一個視窗
        # 建立管理器
        self.enemy_item_manager = ItemManager(self.enemy_equipment_frame, "enemy", self)

        # 按鈕打開道具選擇
        ttk.Button(self.enemy_equipment_frame, text="選擇攜帶道具",
                   command=self.enemy_item_manager.open_item_window).grid(row=999, column=0, pady=10)

        # 顯示目前道具
        ttk.Button(self.enemy_equipment_frame, text="查看道具",
                   command=self.enemy_item_manager.show_current_items).grid(row=999, column=1, pady=10)

        # === 能力值總覽 ===
        self.enemy_overview = CharacterOverviewWnd(self.enemy_frame)
        ttk.Button(self.enemy_frame, text="能力值總覽", command=self.enemy_overview.show_overview_wnd).grid(
            row=9, column=1, pady=10)

        # === 狀態效果欄（放裝備欄下方） ===
        self.enemy_buff_status_bar = StatusEffectBar(self.enemy_frame, gui_ref=self)
        self.enemy_buff_status_bar.grid(
            row=10, column=0, columnspan=2, sticky="ew", pady=5)
        self.enemy_debuff_status_bar = StatusEffectBar(self.enemy_frame, gui_ref=self)
        self.enemy_debuff_status_bar.grid(
            row=11, column=0, columnspan=2, sticky="ew", pady=5)
        self.enemy_passive_status_bar = StatusEffectBar(self.enemy_frame, gui_ref=self)
        self.enemy_passive_status_bar.grid(
            row=12, column=0, columnspan=2, sticky="ew", pady=5)

        # 敵人類型選擇
        ttk.Label(self.enemy_frame, text="敵人類型:").grid(row=0, column=0, sticky=tk.W)
        self.enemy_type_row = ttk.Frame(self.enemy_frame)
        self.enemy_type_row.grid(row=0, column=1, columnspan=3, sticky=tk.W)

        self.enemy_type_var = self.create_var("enemy_type_var", tk.StringVar, "monster")
        ttk.Radiobutton(
            self.enemy_type_row,
            text="怪物",
            variable=self.enemy_type_var,
            value="monster",
            command=self.update_enemy_ui_by_type,
        ).grid(row=0, column=1, sticky=tk.W)
        ttk.Radiobutton(
            self.enemy_type_row,
            text="玩家",
            variable=self.enemy_type_var,
            value="player",
            command=self.update_enemy_ui_by_type,
        ).grid(row=0, column=2, sticky=tk.W)

        self.enemy_type_row.grid_columnconfigure(0, weight=0)
        self.enemy_type_row.grid_columnconfigure(1, weight=0)

        # endregion

        # 戰鬥按鈕
        battle_button = ttk.Button(
            self.main_frame, text="開始戰鬥模擬", command=self.start_battle
        )
        battle_button.grid(row=1, column=0, columnspan=2, pady=10)

        # 暫停
        btn_pause = tk.Button(self.main_frame, text="暫停/繼續", command=toggle_pause)
        btn_pause.grid(row=1, column=1, columnspan=2, pady=10)

        # 戰鬥日誌
        log_frame = ttk.LabelFrame(self.main_frame, text="戰鬥日誌", padding="10")
        log_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E))

        self.log_text = tk.Text(log_frame, height=15,
                                width=80, state=tk.DISABLED)
        self.log_text.pack()

        # 統計按鈕
        stats_frame = ttk.Frame(self.main_frame)
        stats_frame.grid(row=3, column=0, columnspan=2, pady=5)

        ttk.Button(stats_frame, text="傷害分布", command=self.show_damage_stats).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(stats_frame, text="技能使用", command=self.show_skill_stats).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(stats_frame, text="勝率統計", command=self.show_win_rate).pack(
            side=tk.LEFT, padx=5
        )

        root.update_idletasks()

    def common_EquipmentUI(self, frame, prefix):
        """
        通用的裝備以及道具攜帶的UI建立
        """
        # 裝備部位資料
        equipment_vars = {}
        # 裝備部位強化等級資料
        equipment_forge_vars = {}
        # 儲存所有widget參考
        widgets_dict = {}

        parts = list(
            {
                item.WearPartID: item.WearPartID
                for item in GameData.Instance.ArmorsDic.values()
            }.values()
        )
        for i, part in enumerate(parts):
            ttk.Label(frame, text=(CommonFunction.get_text(f"TM_{part}")) + " :").grid(
                row=i, column=0, sticky=tk.W
            )
            armor_id = self.create_var(f"{prefix}_armor_id_{i}", tk.StringVar)
            ttk.Combobox(
                frame,
                textvariable=armor_id,
                values=[
                    CommonFunction.get_text(item.Name)
                    for item in GameData.Instance.ArmorsDic.values()
                    if item.WearPartID == part
                ],
                width=15,
            ).grid(row=i, column=1)
            armor_forge_lv = self.create_var(f"{prefix}_armor_forge_lv_{i}", tk.IntVar, 0)
            armor_forgeLv_spinbox = ttk.Spinbox(
                frame, from_=0, to=10, textvariable=armor_forge_lv, width=5
            )
            armor_forgeLv_spinbox.grid(row=i, column=2)
            armor_forgeLv_spinbox.set(0)
            equipment_vars[part] = (
                # next((k for k, v in GameData.Instance.GameTextDataDic.items() if v.TextContent == armor_id), None)
                armor_id
            )
            equipment_forge_vars[part] = armor_forge_lv

        # 武器（主手 / 副手）
        ttk.Label(frame, text="主手武器:").grid(
            row=len(parts), column=0, sticky=tk.W)

        # 主手武器清單
        mainhandweapon = list(
            weapon
            for weapon in GameData.Instance.WeaponsDic.values()
            if weapon.TakeHandID in ["RightHand", "BothHand", "SingleHand"]
        )
        mainhandweapon_id = self.create_var(f"{prefix}_mainhandweapon_id", tk.StringVar)
        # mainhandweapon_id = tk.StringVar()
        mainhandweapon_combobox = ttk.Combobox(
            frame,
            textvariable=mainhandweapon_id,
            values=[CommonFunction.get_text(weapon.Name)
                    for weapon in mainhandweapon],
            width=15,
        )
        mainhandweapon_combobox.grid(row=len(parts), column=1)
        mainhandweapon_forge_lv = self.create_var(f"{prefix}_mainhandweapon_forge_lv", tk.IntVar, 0)
        mainhandweapon_forgeLv_spinbox = ttk.Spinbox(
            frame, from_=0, to=10, textvariable=mainhandweapon_forge_lv, width=5
        )
        mainhandweapon_forgeLv_spinbox.grid(row=len(parts), column=2)
        mainhandweapon_forgeLv_spinbox.set(0)
        equipment_vars["mainhand"] = (
            mainhandweapon_id
        )
        equipment_forge_vars["mainhand"] = mainhandweapon_forge_lv

        ttk.Label(frame, text="副手武器:").grid(
            row=len(parts) + 1, column=0, sticky=tk.W
        )

        # 副手武器清單
        offhandweapon = list(
            weapon
            for weapon in GameData.Instance.WeaponsDic.values()
            if weapon.TakeHandID in ["SingleHand", "LeftHand"]
        )

        offhandweapon_id = self.create_var(f"{prefix}_offhandweapon_id", tk.StringVar)
        offhandweapon_combobox = ttk.Combobox(
            frame,
            textvariable=offhandweapon_id,
            values=[CommonFunction.get_text(weapon.Name)
                    for weapon in offhandweapon],
            width=15,
        )
        offhandweapon_combobox.grid(row=len(parts) + 1, column=1)
        offhandweapon_forge_lv = self.create_var(f"{prefix}_offhandweapon_forge_lv", tk.IntVar, 0)
        offhandweapon_forgeLv_spinbox = ttk.Spinbox(
            frame, from_=0, to=10, textvariable=offhandweapon_forge_lv, width=5
        )
        offhandweapon_forgeLv_spinbox.grid(row=len(parts) + 1, column=2)
        offhandweapon_forgeLv_spinbox.set(0)
        equipment_vars["offhand"] = (
            # next((k for k, v in GameData.Instance.GameTextDataDic.items() if v.TextContent == offhandweapon_id), None)
            offhandweapon_id
        )
        equipment_forge_vars["offhand"] = offhandweapon_forge_lv

        widgets_dict.update(
            {
                "equipment_vars": equipment_vars,
                "equipment_forge_vars": equipment_forge_vars,
            }
        )
        return widgets_dict

    def update_enemy_ui_by_type(self):
        """根據目前的 enemy_type_var 值來切換 UI 顯示狀態"""
        if self.enemy_type_var.get() == "monster":
            self.enemy_ui_switch(
                True,
                self.enemy_equipment_frame,
                self.enemy_class_label,
                self.enemy_class_combobox,
                self.enemy_lv_label,
                self.enemy_lv_spinbox,
                self.enemy_race_label,
                self.enemy_race_row
            )
            self.enemy_ui_switch(False, self.monster_combobox, self.monster_label)
        else:
            self.enemy_ui_switch(
                False,
                self.enemy_equipment_frame,
                self.enemy_class_label,
                self.enemy_class_combobox,
                self.enemy_lv_label,
                self.enemy_lv_spinbox,
                self.enemy_race_label,
                self.enemy_race_row
            )
            self.enemy_ui_switch(True, self.monster_combobox, self.monster_label)

    def enemy_ui_switch(self, type: bool, *frames):
        """
        對手UI設定切換(玩家與怪物)
        """
        for frame in frames:
            if type:
                frame.grid_remove()
            else:
                frame.grid()

    def start_battle(self):

        # 清空雙方效果欄
        self.player_buff_status_bar.clear_bar()
        self.player_debuff_status_bar.clear_bar()
        self.player_passive_status_bar.clear_bar()
        self.enemy_buff_status_bar.clear_bar()
        self.enemy_debuff_status_bar.clear_bar()
        self.enemy_passive_status_bar.clear_bar()

        # 創建玩家角色
        class_name = self.player_class_var.get()
        jobID = next(
            (key for key, value in self.jobNameDict.items() if value == class_name),
            None,
        )
        jobBonusData = next(
            (c for c in GameData.Instance.JobBonusDic.values() if c.Job == jobID), None
        )
        # 取得職業
        if not jobBonusData:
            messagebox.showerror("錯誤", "請選擇有效的職業")
            return

        self.player_character = self.create_character(
            name=self.player_name.get(),
            race=self.player_race_var.get(),
            jobBonusData=jobBonusData,
            level=self.player_level_var.get(),
            equipment=self.player_equipment_data,
            itemList=[(v["data"], v["count"]) for v in self.player_item_manager.carried_items.values()],
        )

        # 創建敵人
        if self.enemy_type_var.get() == "monster":
            monster_name = self.monster_var.get()
            monster = next(
                (
                    m
                    for m in GameData.Instance.MonstersDataDic.values()
                    if CommonFunction.get_text(m.Name) == monster_name
                ),
                None,
            )

            if not monster:
                messagebox.showerror("錯誤", "請選擇有效的怪物")
                return

            self.enemy_character = self.create_monster_character(monster)
        else:
            # 創建玩家角色
            enemy_class_name = self.enemy_class_var.get()
            enemy_jobID = next(
                (key for key, value in self.jobNameDict.items() if value == enemy_class_name),
                None,
            )
            enemy_jobBonusData = next(
                (c for c in GameData.Instance.JobBonusDic.values() if c.Job == enemy_jobID), None
            )
            # 創建敵對玩家
            self.enemy_character = self.create_character(
                name="敵對玩家",
                race=self.enemy_race_var.get(),
                jobBonusData=enemy_jobBonusData,
                level=self.enemy_level_var.get(),
                equipment=self.enemy_equipment_data,
                itemList=[(v["data"], v["count"]) for v in self.enemy_item_manager.carried_items.values()],
            )

        # 進行戰鬥模擬
        simulator = BattleSimulator(GameData.Instance, self)
        simulator.simulate_battle(self.player_character, self.enemy_character)

        # 儲存使用者配置
        controller.save_view_to_config()

    def create_character(
            self, name: str, race: str, jobBonusData, level: int, equipment={}, itemList=[]
    ) -> BattleCharacter:
        """
        創建人物
        """

        self.weapon_list = [
            (weapon, equipment["equipment_forge_vars"][part_id].get())
            for part_id, var in equipment["equipment_vars"].items()
            for weapon in GameData.Instance.WeaponsDic.values()
            if CommonFunction.get_text(weapon.Name) == var.get()
        ]

        self.armor_list = [
            (armor, equipment["equipment_forge_vars"][part_id].get())
            for part_id, var in equipment["equipment_vars"].items()
            for armor in GameData.Instance.ArmorsDic.values()
            if CommonFunction.get_text(armor.Name) == var.get()
        ]

        # 根據職業和等級計算屬性
        calculator = CharacterStatusCalculator(
            player_data=None,
            weapon_list=self.weapon_list,
            armor_list=self.armor_list,
            game_data=GameData.Instance,
        )
        character_data = calculator.create_character(name, race, jobBonusData, level)

        # 獲取技能
        skills = [
            skill
            for skill in GameData.Instance.SkillDataDic.values()
            if skill.Job == jobBonusData.Job
        ]

        return BattleCharacter(
            name=character_data["name"],
            level=character_data["level"],
            jobBonusData=jobBonusData,
            ai_id=jobBonusData.Job,
            stats=character_data["stats"],
            basal=character_data["basal"],
            equip=character_data["equip"],
            effect=character_data["effect"],
            skills=skills,
            equipped_weapon=self.weapon_list,
            equipped_armor=self.armor_list,
            characterType=True,
            attackTimer=(1 / character_data["stats"]["AS"]),
            buff_bar=self.enemy_buff_status_bar if (name == "敵對玩家") else self.player_buff_status_bar,
            debuff_bar=self.enemy_debuff_status_bar if (name == "敵對玩家") else self.player_debuff_status_bar,
            passive_bar=self.enemy_passive_status_bar if (name == "敵對玩家") else self.player_passive_status_bar,
            items=itemList,
            item_manager=self.enemy_item_manager if (name == "敵對玩家") else self.player_item_manager,
            character_overview=self.enemy_overview if (name == "敵對玩家") else self.player_overview
        )

    def create_monster_character(self, monster) -> BattleCharacter:
        # 將怪物轉換為戰鬥角色
        status_keys = asdict(StatusValues())

        # 用來存怪物實際數值
        stats = status_keys.copy()

        # 把怪物有的欄位塞進去
        monster_stats = {
            "MaxHP": monster.HP,
            "HP": monster.HP,
            "MaxMP": monster.MP,
            "MP": monster.MP,
            "ATK": monster.ATK,
            "DEF": monster.DEF,
            "Crt": monster.Crt,
            "CrtResistance": monster.CrtResistance,
            "CrtDamage": 0,
            "Avoid": monster.Avoid,
            "Hit": monster.Hit,
            "AtkSpeed": monster.AtkSpeed,
            "AttackMode": monster.AttackMode,
            "BlockRate": 0,
            "DamageReduction": 0,
        }

        for k, v in monster_stats.items():
            if k in stats:
                stats[k] = v

        skills = monster.MonsterSkillList

        return BattleCharacter(
            name=CommonFunction.get_text(f"TM_{monster.MonsterCodeID}_Name"),
            jobBonusData=None,
            ai_id=monster.MonsterCodeID,
            level=monster.Lv,
            stats=stats,
            basal=None,
            equip=None,
            effect=None,
            equipped_weapon=None,
            equipped_armor=None,
            skills=skills,
            characterType=False,
            attackTimer=1 / monster.AtkSpeed,
            buff_bar=self.enemy_buff_status_bar,
            debuff_bar=self.enemy_debuff_status_bar,
            passive_bar=self.enemy_passive_status_bar,
            items=[(v["data"], v["count"]) for v in self.enemy_item_manager.carried_items.values()],
            item_manager=self.enemy_item_manager,
            character_overview=self.enemy_overview
        )

    def show_damage_stats(self):
        if not hasattr(self, "last_battle_data"):
            messagebox.showinfo("提示", "請先進行一場戰鬥")
            return

        StatsAnalyzer.plot_damage_distribution(self.last_battle_data["damage"])

    def show_skill_stats(self):
        if not hasattr(self, "last_battle_data"):
            messagebox.showinfo("提示", "請先進行一場戰鬥")
            return

        StatsAnalyzer.plot_skill_usage(self.last_battle_data["player_skill_usage"],
                                       self.last_battle_data["enemy_skill_usage"])

    def show_win_rate(self):
        if not self.battle_results:
            messagebox.showinfo("提示", "請先進行幾場戰鬥")
            return

        win_rate = StatsAnalyzer.calculate_win_rate(self.battle_results)
        messagebox.showinfo(
            "勝率統計",
            f"當前勝率: {win_rate * 100:.1f}% ({sum(self.battle_results)}勝/{len(self.battle_results)}場)",
        )

    def display_battle_log(self, log_lines):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)

        for line in log_lines:
            self._insert_colored_log(line)

        self.log_text.config(state=tk.DISABLED)
        # 滾動到最新訊息
        self.log_text.see(tk.END)

    def _insert_colored_log(self, log_line: str):
        """
        將含有 <color=#xxxxxx>...</color> <b>...</b> <size=XX>...</size> 的字串，動態解析並套用 tkinter 標籤顯示。
        """
        if log_line is None:
            print("⚠️ 偵測到 None 的 battle log！呼叫堆疊如下：")
            traceback.print_stack()  # 會列出是誰呼叫這個函式的
            return  # 不讓程式崩潰

        parts = re.split(r"(<color=#\w+>|</color>|<b>|</b>|<size=\d+>|</size>)", log_line)

        current_tag = {"color": None, "bold": False, "size": None}

        for part in parts:
            if part.startswith("<color="):
                current_tag["color"] = part[7:-1]
            elif part == "</color>":
                current_tag["color"] = None
            elif part == "<b>":
                current_tag["bold"] = True
            elif part == "</b>":
                current_tag["bold"] = False
            elif part.startswith("<size="):
                current_tag["size"] = int(part[6:-1])
            elif part == "</size>":
                current_tag["size"] = None
            elif part:  # 實際文字
                # 建立 tag 名稱
                tag_name = f"color_{current_tag['color']}_b{current_tag['bold']}_s{current_tag['size']}"

                if tag_name not in self.log_text.tag_names():
                    # 建立字型
                    base_font = font.Font(self.log_text, self.log_text.cget("font"))
                    if current_tag["bold"]:
                        base_font.configure(weight="bold")
                    if current_tag["size"]:
                        base_font.configure(size=current_tag["size"])

                    self.log_text.tag_config(tag_name, foreground=current_tag["color"], font=base_font)

                self.log_text.insert(tk.END, part, tag_name)

        self.log_text.insert(tk.END, "\n")

    def call_log(self):
        print("player req width:", self.player_frame.winfo_reqwidth())
        print("enemy  req width:", self.enemy_frame.winfo_reqwidth())
        print("main_frame width:", self.main_frame.winfo_width())


def toggle_pause():
    """
    暫停/繼續 (按鈕觸發)
    """
    os.environ["PAUSED"] = "1" if os.environ.get("PAUSED", "0") == "0" else "0"
    print(f"收到暫停停{os.environ.get("PAUSED")}")


if __name__ == "__main__":
    root = tk.Tk()
    model = UserConfigModel()
    app = BattleSimulatorGUI(root, model)
    controller = UserConfigController(model, app)
    os.environ["PAUSED"] = "0"
    root.mainloop()