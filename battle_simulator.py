import random
from re import S
from typing import Dict, Optional, List
from dataclasses import dataclass
from game_models import SkillData,SkillOperationData, MonsterDataModel, MonsterDropItemDataModel, ArmorDataModel, WeaponDataModel,ItemDataModel,JobBonusDataModel,StatusFormulaDataModel,GameText,GameSettingDataModel,AreaData,LvAndExpDataModel
from formula_parser import FormulaParser
from typing import Tuple
from commonfunction import CommonFunction
# from skill_processor import SkillProcessor

@dataclass
class BattleCharacter:
    name: str
    jobBonusData: JobBonusDataModel
    level: int
    stats: Dict[str, int]
    equipped_weapon: Optional[WeaponDataModel]
    equipped_armor: Optional[ArmorDataModel]
    skills: List[SkillData]
    items: List[ItemDataModel]
    characterType:bool  #當前攻擊者類型 True:人物 False:怪物
    controlled_for_attack:float = 0 #受到控制不得使用普通攻擊類型
    controlled_for_skill:float = 0  #受到控制不得使用技能類型
    attackTimer:float = 0   #普通攻擊計時器
    attackTimerFunc = None #儲存普攻計時任務

    def action_check(self,skill:SkillData)->bool:
        if(skill.Name == "普通攻擊"):
            return self.stats["HP"] > 0 & self.controlled_for_attack <=0
        else:
            return self.stats["HP"] > 0 & self.controlled_for_skill <=0

    def is_alive(self) -> bool:
        return self.stats["HP"] > 0

    def PassTimeControll(self,passtime:float):
        """
        處理經過時間
        """
        if(controlled_for_attack!=0):
            controlled_for_attack = CommonFunction.clamp((controlled_for_attack-passtime),0,controlled_for_attack);
        if(controlled_for_skill!=0):
            controlled_for_skill = CommonFunction.clamp((controlled_for_skill-passtime),0,controlled_for_skill);
    
    def CrowdControlCalculator(self,op: SkillOperationData):
        """
        控制效果計算
        """
        match(op.InfluenceStatus):
            case "Taunt" | "Stun":
                controlled_for_skill+=op.EffectDurationTime
                controlled_for_attack+=op.EffectDurationTime

    def HitCalculator(self, skill: SkillData, target) -> Tuple[str, int, int]:
        """
        命中計算
        """
        selfHit = 0;
        if self.characterType:
            if(skill.Name !="普通攻擊"):
                match skill.AdditionMode:
                    case "MeleeATK":
                        selfHit = self.stats["MeleeHit"];
                    case "RemoteATK":
                        selfHit = self.stats["RemoteHit"];
                    case "MageATK":
                        selfHit = self.stats["MageHit"];
                    case _:
                        print("未知屬性")
            else:
                selfHit = self.stats["MeleeHit"];
        else:
            selfHit = self.stats["Hit"];
        
        # 命中率 四捨五入取整數
        hit_value = round(selfHit * 100 /max(1, selfHit + target.stats["Avoid"]))
        # 命中判定  0～100 隨機
        is_hit = random.randint(0, 100)
        
        if is_hit <= hit_value:
            return self.BlockCalculator(skill,target)
        else:
            return f" <color=#00ffdc>{self.name}</color> 使用 <color=#ff9300>{CommonFunction.get_text(skill.Name)}</color> 但攻擊並沒有命中！", 0, self.attackTimer
    
    def BlockCalculator(self, skill: SkillData, target)-> Tuple[str, int, int]:
        """
        格檔計算
        """
        is_block = random.randint(0,100)    
        if(is_block <= self.stats["BlockRate"]):
            return f" <color=#00ffdc>{self.name}</color> 使用 <color=#ff9300>{CommonFunction.get_text(skill.Name)}</color> 但被格檔了！", 0, self.attackTimer
        else:
            return self.CrtCalculator(skill,target)
            
    def CrtCalculator(self, skill: SkillData, target)-> Tuple[str, int, int]:
        """
        暴擊計算
        """
        #暴擊率 
        crt_resistance = self.stats["Crt"] + target.stats["CrtResistance"]
        crt_value = 0
        if crt_resistance!=0:
            crt_value = round(self.stats["Crt"] * 100 / (self.stats["Crt"] + crt_resistance))
        #暴擊判定
        is_Crt = random.randint(0,100)
        
        return self.AttackCalculator(skill,target,(is_Crt<=crt_value));
            
    def AttackCalculator(self, skill: SkillData, target,is_Crt:bool) -> Tuple[str, int, int]:
        """
        攻擊計算
        """
        selfATK = 0;
        targetDEF = 0;
        if self.characterType:
            if skill.Name !="普通攻擊":
                match skill.AdditionMode:
                    case "MeleeATK":
                        selfATK = self.stats["MeleeATK"];
                        targetDEF = target.stats["DEF"];
                    case "RemoteATK":
                        selfATK = self.stats["RemoteATK"];
                        targetDEF = target.stats["DEF"];
                    case "MageATK":
                        selfATK = self.stats["MageATK"];
                        targetDEF = target.stats["MDEF"];
                    case _:
                        print("未知屬性")
            else:
                selfATK = self.stats["MeleeATK"];
                targetDEF = target.stats["DEF"];
        else:
            selfATK = self.stats["ATK"];
            match self.stats["AttackMode"]:
                case "MeleeATK":
                    targetDEF = target.stats["DEF"];
                case "RemoteATK":
                    targetDEF = target.stats["DEF"];
                case "MageATK":
                    targetDEF = target.stats["MDEF"];
                case _:
                    print("未知屬性")

        # 實現技能效果
        parser = FormulaParser()
        variables = {
                "attacker_attack": selfATK, #攻擊者的攻擊力
                "target_defense": targetDEF, #受攻擊者防禦
                "skill_power": skill.Damage,  #傷害倍率
                "attacker_level": self.level, #攻擊者等級
                "target_level": target.level, #受攻擊者等級
                "random_factor": random.uniform(0.85, 1.15),
                "base_damage": skill.Damage
        }
        parser.set_variables(variables)

        #計算防禦減免
        defenseRatio = CommonFunction.clamp(variables["target_defense"] / (variables["target_defense"] + 9), 0.1, 0.75)
        print(f"技能傷害倍率:{skill.Damage}")
        #計算傷害
        if is_Crt:
            damage = round(variables["attacker_attack"]*int(skill.Damage)*1.5)+self.stats["CrtDamage"]
        else:
            damage = round(variables["attacker_attack"]*int(skill.Damage))

        finalDamage = CommonFunction.clamp(round(damage * (1 - defenseRatio)) - target.stats["DamageReduction"],0,round(damage * (1 - defenseRatio)) - target.stats["DamageReduction"])
        print(f"攻擊對象:{self.characterType}，攻擊者傷害:{damage}，防禦減免{defenseRatio}，最後傷害{finalDamage}")
        
        target.stats["HP"] -= finalDamage
        self.stats["MP"] -= skill.CastMage
        
        color_code = '#ffba01' if is_Crt else '#ff0000'
        
        return f" <color=#00ffdc>{self.name}</color> 使用 <color=#ff9300>{CommonFunction.get_text(skill.Name)}</color> 對  <color=#83ff00>{target.name}</color> 造成 <color={color_code}>{finalDamage}</color> 傷害！", finalDamage, self.attackTimer

class BattleSimulator:
    def __init__(self, game_data,gui):
        self.game_data = game_data
        self.gui = gui
        self.battle_log: List[str] = []
        self.damage_data: List[Dict] = []
        self.skill_usage: Dict[str, int] = {}
        self.update_hp_mp = None    #用來儲存更新雙方血量魔力的匿名方法


    def simulate_battle(self, player: BattleCharacter, enemy: BattleCharacter):
        """開啟戰鬥模擬"""
        self.battle_log.clear()
        self.damage_data.clear()
        self.skill_usage = {s.Name: 0 for s in player.skills}
        
        #匿名方法 更新雙方血量魔力
        def update_hp_mp():
            self.gui.player_hp_bar.set_value(player.stats["HP"],player.stats["MaxHP"])
            self.gui.player_mp_bar.set_value(player.stats["MP"],player.stats["MaxMP"])
            self.gui.enemy_hp_bar.set_value(enemy.stats["HP"],enemy.stats["MaxHP"])
            self.gui.enemy_mp_bar.set_value(enemy.stats["MP"],enemy.stats["MaxMP"])        
        self.update_hp_mp = update_hp_mp
        
        #初始化雙方血量魔力
        self.update_hp_mp()
        
        #雙方同時運作攻擊計時器
        self.attack_loop(player, enemy)
        self.attack_loop(enemy, player)
    
    def check_battle_result(self, player: BattleCharacter, enemy: BattleCharacter):
        """
        進行戰鬥結果確認
        """
        if player.is_alive():
            print(f"{enemy.name} 被擊敗了！{player.name} 獲勝！")
            self.battle_log.append(f"{enemy.name} 被擊敗了！{player.name} 獲勝！")
            self.gui.battle_results.append(True);
        else:
            print(f"{player.name} 被擊敗了！{enemy.name} 獲勝！")
            self.battle_log.append(f"{player.name} 被擊敗了！{enemy.name} 獲勝！")
        
        self.gui.display_battle_log(self.get_battle_log());
            # 保存戰鬥數據用於統計
        self.gui.last_battle_data = {
            "damage": self.get_damage_data(),
            "skill_usage": self.get_skill_usage(),
            "result": player.is_alive()
        }

    def attack_loop(self, attacker: BattleCharacter, target):
        """獨立的攻擊計時器迴圈"""
        
        if attacker.is_alive() and target.is_alive():
            skill = self._choose_skill(attacker)
            if attacker.action_check(skill):
                log_msg, damage, attack_timer = attacker.HitCalculator(skill, target)
                self.battle_log.append(log_msg)
                if(skill.SkillID == "NORMAL_ATTACK"):
                    self.battle_log.append(f"<color=#00ffdc>{attacker.name}</color> 進入<color=#ff0000>普攻</color>計時 {attack_timer:.2f} 秒")
                    self.gui.display_battle_log(self.get_battle_log());
                    attacker.attackTimerFunc = self.gui.root.after(int(attack_timer*1000) ,lambda: self.attack_loop(attacker, target))
                else:
                    self.battle_log.append(f"<color=#00ffdc>{attacker.name}</color> 施放了 <color=#ff0000>{CommonFunction.get_text(skill.Name)}</color> 需等待 {skill.CD} 秒")
                    self.gui.display_battle_log(self.get_battle_log());
                    attacker.attackTimerFunc = self.gui.root.after(int(skill.CD*1000) ,lambda: self.attack_loop(attacker, target))
                #更新雙方血量魔力
                self.update_hp_mp()
            else:
                attacker.attackTimerFunc = self.gui.root.after(100, lambda: self.attack_loop(attacker, target))
        else:
            if(attacker.attackTimerFunc is not None):
                self.gui.root.after_cancel(attacker.attackTimerFunc)
                self.check_battle_result(attacker,target)
        
    def _choose_skill(self, character: BattleCharacter) -> SkillData :
        # 簡單的AI選擇技能邏輯
        available_skills = [s for s in character.skills if character.stats["MP"] >= s.CastMage]
        if not available_skills:
            # 沒有MP時使用普通攻擊
            return SkillData(
                    SkillID="NORMAL_ATTACK",
                    Name="普通攻擊",
                    Damage=1,
                    CastMage=0,
                     # 其他必要參數...
            )
        return random.choice(available_skills) 

    def get_battle_log(self) -> List[str]:
        return self.battle_log
    
    def get_damage_data(self) -> List[Dict]:
        return self.damage_data
    
    def get_skill_usage(self) -> Dict[str, int]:
        return self.skill_usage