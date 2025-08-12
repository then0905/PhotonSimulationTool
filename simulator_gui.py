# -*- coding: utf-8 -*-
from ast import Lambda
from multiprocessing import Value
from optparse import Values
import tkinter as tk
from tkinter import ttk, messagebox
from game_models import GameData
from battle_simulator import BattleSimulator, BattleCharacter
from stats_analyzer import StatsAnalyzer
from status_operation import CharacterStatusCalculator
from commonfunction import CommonFunction
from typing import Dict

class BattleSimulatorGUI:
    jobNameDict: Dict[str, str] = {}
    
    def __init__(self, root):
        self.root = root
        self.root.title("UnityAI")
        
        # 加載遊戲數據
        self.game_data = GameData()
        
        # 創建界面
        self.create_widgets()
        
        # 初始化變量
        self.player_character = None
        self.enemy_character = None
        self.battle_results = []
        
    def create_widgets(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        class ColoredBar(tk.Canvas):
            """
            彩色條
            """
            def __init__(self, master, width=200, height=20, fg_color="red", **kwargs):
                super().__init__(master, width=width, height=height, bg="gray20", highlightthickness=0, **kwargs)
                self.width = width
                self.height = height
                self.fg_color = fg_color
                self.current_value = 0
                self.max_value = 100
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
                self.create_rectangle(0, 0, bar_width, self.height, fill=self.fg_color, outline="")
                self.create_text(self.width // 2, self.height // 2,
                            text=f"{self.current_value}/{self.max_value}",
                            fill="white", font=("Arial", 10, "bold"))
                
        #region 左側玩家設置
        
        player_frame = ttk.LabelFrame(main_frame, text="玩家設置", padding="20")
        player_frame.grid(row=0, column=0, sticky=tk.N, padx=5, pady=5)
        
        # 角色名稱
        ttk.Label(player_frame, text="角色名稱:").grid(row=0, column=0, sticky=tk.W)
        self.player_name = tk.StringVar(value="玩家1")
        ttk.Entry(player_frame, textvariable=self.player_name,width = 15).grid(row=0, column=1)

        # 職業選擇
        ttk.Label(player_frame, text="職業:").grid(row=1, column=0, sticky=tk.W)
        self.player_class_var = tk.StringVar()
        
        for jobData in GameData.Instance.JobBonusDic.values():
            self.jobNameDict.update({jobData.Job: CommonFunction.get_text("TM_"+jobData.Job)})
        tempJobNameList = list(self.jobNameDict.values())
        
        ttk.Combobox(player_frame, textvariable=self.player_class_var, values=tempJobNameList,width = 15).grid(row=1, column=1)
        self.player_class_var.set(next(iter(self.jobNameDict.values())))
            
        #角色血量
        self.player_hp_bar = ColoredBar(player_frame, width=150, height=20, fg_color="red")
        self.player_hp_bar.grid(row=2, column=1, columnspan=2, pady=2)
        self.player_hp_bar.set_value(100, 100)  # 預設滿血，可根據角色資料初始化
        
        #角色魔力
        self.player_mp_bar = ColoredBar(player_frame, width=150, height=20, fg_color="blue")
        self.player_mp_bar.grid(row=3, column=1, columnspan=2, pady=2)
        self.player_mp_bar.set_value(50, 50)  # 預設滿魔力，可根據角色資料初始化
        
        # 等級
        ttk.Label(player_frame, text="等級:").grid(row=4, column=0, sticky=tk.W)
        self.player_level_var = tk.IntVar(value=1)
        ttk.Spinbox(player_frame, from_=1, to=100, textvariable=self.player_level_var,width = 15).grid(row=4, column=1)
        self.player_level_var.set(1)
        
        # 左側裝備區
        player_equipment_frame = ttk.LabelFrame(player_frame, text="裝備欄", padding="10")
        player_equipment_frame.grid(row=5, column=0,columnspan=2, padx=1, pady=1, sticky=tk.W)
        self.player_equipment_data = self.common_EquipmentUI(player_equipment_frame)
        # === 道具按鈕 ===
        ttk.Button(player_equipment_frame, text="選擇攜帶道具", command=self.open_item_window).grid(row=999, column=0, pady=10)


        #endregion
   
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
        enemy_frame = ttk.LabelFrame(main_frame, text="敵人設置", padding="20")
        enemy_frame.grid(row=0, column=1, sticky=tk.N, padx=5, pady=5)
        enemy_frame.columnconfigure(0, minsize=60)
        enemy_frame.columnconfigure(1, minsize=60)
        enemy_frame.columnconfigure(2, minsize=60)
        enemy_frame.columnconfigure(3, minsize=60)
        enemy_frame.columnconfigure(4, minsize=60)
        
        # 怪物選擇
        monster_label = ttk.Label(enemy_frame, text="選擇怪物:")
        monster_label.grid(row=1, column=0, sticky=tk.W)
        self.monster_var = tk.StringVar()
        monsters = [m.MonsterCodeID for m in GameData.Instance.MonstersDataDic.values()]
        monster_combobox = ttk.Combobox(enemy_frame, textvariable=self.monster_var, values=monsters,width = 15)
        monster_combobox.grid(row=1, column=1, columnspan=1)
        if monsters:
            self.monster_var.set(monsters[0])

        #敵對玩家職業
        enemy_class_label = ttk.Label(enemy_frame, text="職業:")
        enemy_class_label.grid(row=2, column=0, sticky=tk.W)
        self.enemy_class_var = tk.StringVar()
        for jobData in GameData.Instance.JobBonusDic.values():
            self.jobNameDict.update({jobData.Job: CommonFunction.get_text("TM_"+jobData.Job)})
            
        tempJobNameList = list(self.jobNameDict.values())
        enemy_class_combobox = ttk.Combobox(enemy_frame, textvariable=self.enemy_class_var, values=tempJobNameList,width = 15)
        enemy_class_combobox.grid(row=2, column=1)
        
        self.enemy_class_var.set(next(iter(self.jobNameDict.values())))

        # 敵對玩家等級
        enemy_lv_label = ttk.Label(enemy_frame, text="等級:")
        enemy_lv_label.grid(row=5, column=0, sticky=tk.W)
        self.enemy_level_var = tk.IntVar(value=1)
        enemy_lv_spinbox = ttk.Spinbox(enemy_frame, from_=1, to=100, textvariable=self.enemy_level_var,width = 15)
        enemy_lv_spinbox.grid(row=5, column=1)
        
        #角色血量
        self.enemy_hp_bar = ColoredBar(enemy_frame, width=150, height=20, fg_color="red")
        self.enemy_hp_bar.grid(row=3, column=1, columnspan=2, pady=2)
        self.enemy_hp_bar.set_value(100, 100)  # 預設滿血，可根據角色資料初始化
        #角色魔力
        self.enemy_mp_bar = ColoredBar(enemy_frame, width=150, height=20, fg_color="blue")
        self.enemy_mp_bar.grid(row=4, column=1, columnspan=2, pady=2)
        self.enemy_mp_bar.set_value(50, 50)  # 預設滿魔力，可根據角色資料初始化
        
        # 右側裝備區
        enemy_equipment_frame = ttk.LabelFrame(enemy_frame, text="裝備欄", padding="5")
        enemy_equipment_frame.grid(row=5, column=0,columnspan=2, padx=1, pady=1, sticky=tk.W)
        self.enemy_equipment_data = self.common_EquipmentUI(enemy_equipment_frame)
        # === 道具按鈕 ===
        ttk.Button(enemy_equipment_frame, text="選擇攜帶道具", command=self.open_item_window).grid(row=10, column=0, pady=10)
        
        # 敵人類型選擇
        ttk.Label(enemy_frame, text="敵人類型:").grid(row=0, column=0, sticky=tk.W) 
        self.enemy_type_var = tk.StringVar(value="monster")
        ttk.Radiobutton(enemy_frame, text="怪物", variable=self.enemy_type_var, value="monster",command = lambda:(self.enemy_ui_switch(True,enemy_equipment_frame,enemy_class_label,enemy_class_combobox,enemy_lv_label,enemy_lv_spinbox),self.enemy_ui_switch(False,monster_combobox,monster_label))).grid(row=0, column=1, sticky=tk.W)
        ttk.Radiobutton(enemy_frame, text="玩家", variable=self.enemy_type_var, value="player",command = lambda:(self.enemy_ui_switch(False,enemy_equipment_frame,enemy_class_label,enemy_class_combobox,enemy_lv_label,enemy_lv_spinbox),self.enemy_ui_switch(True,monster_combobox,monster_label))).grid(row=0, column=2, sticky=tk.W)
        if self.enemy_type_var.get() == "monster":
            self.enemy_ui_switch(True,enemy_equipment_frame,enemy_class_label,enemy_class_combobox,enemy_lv_label,enemy_lv_spinbox)
        else:
            self.enemy_ui_switch(False,enemy_equipment_frame,enemy_class_label,enemy_class_combobox,enemy_lv_label,enemy_lv_spinbox)
       
        #endregion    

        # 戰鬥按鈕
        battle_button = ttk.Button(main_frame, text="開始戰鬥模擬", command=self.start_battle)
        battle_button.grid(row=1, column=0, columnspan=2, pady=10)
        
        # 戰鬥日誌
        log_frame = ttk.LabelFrame(main_frame, text="戰鬥日誌", padding="10")
        log_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E))
        
        self.log_text = tk.Text(log_frame, height=15, width=80, state=tk.DISABLED)
        self.log_text.pack()
        
        # 統計按鈕
        stats_frame = ttk.Frame(main_frame)
        stats_frame.grid(row=3, column=0, columnspan=2, pady=5)
        
        ttk.Button(stats_frame, text="傷害分布", command=self.show_damage_stats).pack(side=tk.LEFT, padx=5)
        ttk.Button(stats_frame, text="技能使用", command=self.show_skill_stats).pack(side=tk.LEFT, padx=5)
        ttk.Button(stats_frame, text="勝率統計", command=self.show_win_rate).pack(side=tk.LEFT, padx=5)
    


    def common_EquipmentUI(self,frame):
        """
        通用的裝備以及道具攜帶的UI建立
        """
        # 裝備部位資料
        equipment_vars = {}
        # 裝備部位強化等級資料
        equipment_forge_vars = {}
        #儲存所有widget參考
        widgets_dict = {} 

        parts = list({item.WearPartID: item.WearPartID for item in GameData.Instance.ArmorsDic.values()}.values())
        for i, part in enumerate(parts):
            ttk.Label(frame, text=(CommonFunction.get_text(f"TM_{part}"))+" :").grid(row=i, column=0, sticky=tk.W)
            armor_id = tk.StringVar()        
            ttk.Combobox(frame, textvariable=armor_id, values=[CommonFunction.get_text(item.Name) for item in GameData.Instance.ArmorsDic.values() if item.WearPartID == part],width=15).grid(row=i, column=1)
            armor_forge_lv = tk.IntVar(value=0)
            armor_forgeLv_spinbox = ttk.Spinbox(frame, from_=0, to=10, textvariable=armor_forge_lv, width=5)
            armor_forgeLv_spinbox.grid(row=i, column=2)
            armor_forgeLv_spinbox.set(0)
            equipment_vars[part] = armor_id#next((k for k, v in GameData.Instance.GameTextDataDic.items() if v.TextContent == armor_id), None)
            equipment_forge_vars[part] = armor_forge_lv

        # 武器（主手 / 副手）
        ttk.Label(frame, text="主手武器:").grid(row=len(parts), column=0, sticky=tk.W)
        
        #主手武器清單
        mainhandweapon = list(weapon for weapon in GameData.Instance.WeaponsDic.values() if weapon.TakeHandID in ["RightHand", "BothHand", "SingleHand"])
        
        mainhandweapon_id = tk.StringVar()
        mainhandweapon_combobox = ttk.Combobox(frame, textvariable=mainhandweapon_id, values=[CommonFunction.get_text(weapon.Name)for weapon in mainhandweapon],width=15)
        mainhandweapon_combobox.grid(row=len(parts), column=1)
        mainhandweapon_forge_lv = tk.IntVar(value=0)
        mainhandweapon_forgeLv_spinbox = ttk.Spinbox(frame, from_=0, to=10, textvariable=mainhandweapon_forge_lv, width=5)
        mainhandweapon_forgeLv_spinbox.grid(row=len(parts), column=2)
        mainhandweapon_forgeLv_spinbox.set(0)
        equipment_vars["mainhand"] = mainhandweapon_id#next((k for k, v in GameData.Instance.GameTextDataDic.items() if v.TextContent == mainhandweapon_id), None)
        equipment_forge_vars["mainhand"] = mainhandweapon_forge_lv
        
        ttk.Label(frame, text="副手武器:").grid(row=len(parts)+1, column=0, sticky=tk.W)
        
        #副手武器清單
        offhandweapon = list(weapon for weapon in GameData.Instance.WeaponsDic.values() if weapon.TakeHandID in ["SingleHand", "LeftHand"])
        
        offhandweapon_id = tk.StringVar()
        offhandweapon_combobox = ttk.Combobox(frame, textvariable=offhandweapon_id, values=[CommonFunction.get_text(weapon.Name)for weapon in offhandweapon],width=15)
        offhandweapon_combobox.grid(row=len(parts)+1, column=1)
        offhandweapon_forge_lv = tk.IntVar(value=0)
        offhandweapon_forgeLv_spinbox =  ttk.Spinbox(frame, from_=0, to=10, textvariable=offhandweapon_forge_lv, width=5)
        offhandweapon_forgeLv_spinbox.grid(row=len(parts)+1, column=2)
        offhandweapon_forgeLv_spinbox.set(0)
        equipment_vars["offhand"] = offhandweapon_id#next((k for k, v in GameData.Instance.GameTextDataDic.items() if v.TextContent == offhandweapon_id), None)
        equipment_forge_vars["offhand"] = offhandweapon_forge_lv

        widgets_dict.update({
        'equipment_vars': equipment_vars,
        'equipment_forge_vars': equipment_forge_vars
    })
        return widgets_dict

    def enemy_ui_switch(self,type:bool,*frames):
        """
        對手UI設定切換(玩家與怪物)
        """
        for frame in frames:
            if(type):
                frame.grid_remove()
            else:
                frame.grid()

    def open_item_window(self):
        """
        道具面板的呼叫
        """
        item_window = tk.Toplevel(self.root)
        item_window.title("道具選擇")
        
        self.item_vars = {}
        self.item_counts = {}

        #過濾出 有技能效果(可作用的部分)
        filtered_items = [item for item in GameData.Instance.ItemsDic.values() if len(item.ItemEffectDataList) > 0]
        
        for i,item in enumerate (filtered_items):
            var = tk.BooleanVar()
            count_var = tk.IntVar(value=1)
            self.item_vars[item.CodeID] = var
            self.item_counts[item.CodeID] = count_var

            ttk.Checkbutton(item_window, text=CommonFunction.get_text(item.Name), variable=var).grid(row=i, column=0, sticky=tk.W)
            ttk.Spinbox(item_window, from_=1, to=99, textvariable=count_var, width=5).grid(row=i, column=1)

        ttk.Button(item_window, text="確定", command=item_window.destroy).grid(row=len(filtered_items), column=0, columnspan=2, pady=10)

    def start_battle(self):
        # 創建玩家角色
        class_name = self.player_class_var.get()
        jobID = next((key for key, value in self.jobNameDict.items() if value == class_name), None)
        jobBonusData = next((c for c in GameData.Instance.JobBonusDic.values() if c.Job == jobID), None)
        #取得職業
        if not jobBonusData:
            messagebox.showerror("錯誤", "請選擇有效的職業")
            return
                    
        self.player_character = self.create_character(
            name=self.player_name.get(),
            jobBonusData=jobBonusData,
            level=self.player_level_var.get(),
            equipment=self.player_equipment_data
        )

        # 創建敵人
        if self.enemy_type_var.get() == "monster":
            monster_name = self.monster_var.get()
            monster = next((m for m in GameData.Instance.MonstersDataDic.values() if m.MonsterCodeID == monster_name), None)
            
            if not monster:
                messagebox.showerror("錯誤", "請選擇有效的怪物")
                return
            
            self.enemy_character = self.create_monster_character(monster)
        else:
            # 創建敵對玩家
            self.enemy_character = self.create_character(
                name="敵對玩家",
                jobBonusData=jobBonusData,  # 使用相同的職業
                level=self.enemy_level_var.get(),
                equipment=self.enemy_equipment_data
            )

        # 進行戰鬥模擬
        simulator = BattleSimulator(GameData.Instance,self)
        simulator.simulate_battle(self.player_character, self.enemy_character)
    
    def create_character(self, name: str, jobBonusData, level: int , equipment = {}) -> BattleCharacter:
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
        game_data=GameData.Instance
        )
        character_data = calculator.create_character(name, jobBonusData, level)
        
        # 獲取技能
        skills = [
                skill
                for skill in GameData.Instance.SkillDataDic.values()
                if skill.Job == jobBonusData.Job and skill.Characteristic is True
]    
        
        return BattleCharacter(
        name=character_data["name"],
        level=character_data["level"],
        jobBonusData=jobBonusData,
        stats=character_data["stats"],
        skills=skills,
        items=[],
        equipped_weapon=self.weapon_list,
        equipped_armor=self.armor_list,
        characterType=True,
        attackTimer=(1/character_data["stats"]["AS"])
        )
    
    def create_monster_character(self, monster) -> BattleCharacter:
        # 將怪物轉換為戰鬥角色
        stats = {
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
            "AttackMode" : monster.AttackMode,
            "BlockRate" :0,
            "DamageReduction": 0,
        }
        
        skills = monster.MonsterSkillList
        
        return BattleCharacter(
            name=CommonFunction.get_text(f"TM_{monster.MonsterCodeID}_Name"),
            jobBonusData=None,
            level=monster.Lv,
            stats=stats,
            equipped_weapon=None,
            equipped_armor=None,
            skills=skills,
            items=[],
            characterType=False,
            attackTimer = 1/monster.AtkSpeed
        )
    
    def show_damage_stats(self):
        if not hasattr(self, 'last_battle_data'):
            messagebox.showinfo("提示", "請先進行一場戰鬥")
            return
        
        StatsAnalyzer.plot_damage_distribution(self.last_battle_data["damage"])
    
    def show_skill_stats(self):
        if not hasattr(self, 'last_battle_data'):
            messagebox.showinfo("提示", "請先進行一場戰鬥")
            return
        
        StatsAnalyzer.plot_skill_usage(self.last_battle_data["skill_usage"])
    
    def show_win_rate(self):
        if not self.battle_results:
            messagebox.showinfo("提示", "請先進行幾場戰鬥")
            return
        
        win_rate = StatsAnalyzer.calculate_win_rate(self.battle_results)
        messagebox.showinfo("勝率統計", f"當前勝率: {win_rate*100:.1f}% ({sum(self.battle_results)}勝/{len(self.battle_results)}場)")
    
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
        將含有 <color=#xxxxxx>...</color> 的字串，動態解析顏色並套用 tkinter 標籤顯示。
        會自動為每種出現的顏色建立一個 tag。
        """
        import re;

        parts = re.split(r'(<color=#\w+>|</color>)', log_line)
        current_tag = None

        for part in parts:
            if part.startswith("<color="):
                color_code = part[7:-1].lower()
                tag_name = f"color_{color_code[1:]}"  # e.g. color_ff0000

                # 如果這個 tag 沒定義過，就定義一個
                if not self.log_text.tag_names().__contains__(tag_name):
                    self.log_text.tag_config(tag_name, foreground=color_code)

                current_tag = tag_name

            elif part == "</color>":
                current_tag = None

            else:
                self.log_text.insert(tk.END, part, current_tag)

        self.log_text.insert(tk.END, "\n")

if __name__ == "__main__":
    root = tk.Tk()
    app = BattleSimulatorGUI(root)
    root.mainloop()