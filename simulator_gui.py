# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Dict, List
from game_models import GameData,SkillDataDic,MonstersDataDic,MonsterDropItemDic,ArmorsDic,WeaponsDic,ItemsDic,JobBonusDic,StatusFormulaDic,GameTextDataDic,GameSettingDic,AreaDataDic,ExpAndLvDic
from battle_simulator import BattleSimulator, BattleCharacter
from stats_analyzer import StatsAnalyzer
from status_operation import CharacterStatusCalculator

class BattleSimulatorGUI:
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
        
        # 左側玩家設置
        player_frame = ttk.LabelFrame(main_frame, text="玩家設置", padding="10")
        player_frame.grid(row=0, column=0, sticky=tk.N, padx=5, pady=5)
        
        # 角色名稱
        ttk.Label(player_frame, text="角色名稱:").grid(row=0, column=0, sticky=tk.W)
        self.player_name = tk.StringVar(value="玩家1")
        ttk.Entry(player_frame, textvariable=self.player_name).grid(row=0, column=1)
        
        # 職業選擇
        ttk.Label(player_frame, text="職業:").grid(row=1, column=0, sticky=tk.W)
        self.class_var = tk.StringVar()
        classes = [c.Job for c in self.game_data.JobBonusDic.values()]
        ttk.Combobox(player_frame, textvariable=self.class_var, values=classes).grid(row=1, column=1)
        if classes:
            self.class_var.set(classes[0])
        
        # 等級
        ttk.Label(player_frame, text="等級:").grid(row=2, column=0, sticky=tk.W)
        self.level_var = tk.IntVar(value=1)
        ttk.Spinbox(player_frame, from_=1, to=100, textvariable=self.level_var).grid(row=2, column=1)
        
        # 右側敵人設置
        enemy_frame = ttk.LabelFrame(main_frame, text="敵人設置", padding="10")
        enemy_frame.grid(row=0, column=1, sticky=tk.N, padx=5, pady=5)
        
        # 敵人類型選擇
        ttk.Label(enemy_frame, text="敵人類型:").grid(row=0, column=0, sticky=tk.W)
        self.enemy_type_var = tk.StringVar(value="monster")
        ttk.Radiobutton(enemy_frame, text="怪物", variable=self.enemy_type_var, value="monster").grid(row=0, column=1, sticky=tk.W)
        ttk.Radiobutton(enemy_frame, text="玩家", variable=self.enemy_type_var, value="player").grid(row=0, column=2, sticky=tk.W)
        
        # 怪物選擇
        ttk.Label(enemy_frame, text="選擇怪物:").grid(row=1, column=0, sticky=tk.W)
        self.monster_var = tk.StringVar()
        monsters = [m.MonsterCodeID for m in self.game_data.MonstersDataDic.values()]
        self.monster_combobox = ttk.Combobox(enemy_frame, textvariable=self.monster_var, values=monsters)
        self.monster_combobox.grid(row=1, column=1, columnspan=2)
        if monsters:
            self.monster_var.set(monsters[0])
        
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
    
    def start_battle(self):
        # 創建玩家角色
        class_name = self.class_var.get()
        jobBonusData = next((c for c in self.game_data.JobBonusDic.values() if c.Job == class_name), None)
        
        if not jobBonusData:
            messagebox.showerror("錯誤", "請選擇有效的職業")
            return
        
        self.player_character = self.create_character(
            name=self.player_name.get(),
            jobBonusData=jobBonusData,
            level=self.level_var.get()
        )

        # 創建敵人
        if self.enemy_type_var.get() == "monster":
            monster_name = self.monster_var.get()
            monster = next((m for m in self.game_data.MonstersDataDic.values() if m.MonsterCodeID == monster_name), None)
            
            if not monster:
                messagebox.showerror("錯誤", "請選擇有效的怪物")
                return
            
            self.enemy_character = self.create_monster_character(monster)
        else:
            # 創建敵對玩家
            self.enemy_character = self.create_character(
                name="敵對玩家",
                jobBonusData=jobBonusData,  # 使用相同的職業
                level=self.level_var.get()
            )
        
        # 進行戰鬥模擬
        simulator = BattleSimulator(self.game_data)
        result = simulator.simulate_battle(self.player_character, self.enemy_character)
        self.battle_results.append(result)
        
        # 顯示戰鬥日誌
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.insert(tk.END, "\n".join(simulator.get_battle_log()))
        self.log_text.config(state=tk.DISABLED)
        
        # 保存戰鬥數據用於統計
        self.last_battle_data = {
            "damage": simulator.get_damage_data(),
            "skill_usage": simulator.get_skill_usage(),
            "result": result
        }
    
    def create_character(self, name: str, jobBonusData, level: int) -> BattleCharacter:
        # 根據職業和等級計算屬性
        calculator = CharacterStatusCalculator(
        player_data=None,  # 用 .create_character() 自行創建
        weapon_list=[],
        armor_list=[],
        game_data=self.game_data
        )
        character_data = calculator.create_character(name, jobBonusData, level)
        
        # 獲取技能
        skills = [
                skill
                for skill in self.game_data.SkillDataDic.values()
                if skill.Job == jobBonusData.Job and skill.Characteristic is True
]    
        
        return BattleCharacter(
        name=character_data["name"],
        level=character_data["level"],
        jobBonusData=jobBonusData,
        stats=character_data["stats"],
        skills=skills,
        items=[],
        equipped_weapon=None,
        equipped_armor=None
        )
    
    def create_monster_character(self, monster) -> BattleCharacter:
        # 將怪物轉換為戰鬥角色
        stats = {
            "hp": monster.HP,
            "mp": monster.MP,  # 示例值
            "attack": monster.MeleeATK,
            "defense": monster.DEF,
            "magic_attack": monster.MageATK,
            "magic_defense": monster.MDEF
        }
        
        skills = monster.MonsterSkillList
        
        return BattleCharacter(
            name=monster.MonsterCodeID,
            jobBonusData=None,
            level=monster.Lv,
            stats=stats,
            equipped_weapon=None,
            equipped_armor=None,
            skills=skills,
            items=[]
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

if __name__ == "__main__":
    root = tk.Tk()
    app = BattleSimulatorGUI(root)
    root.mainloop()