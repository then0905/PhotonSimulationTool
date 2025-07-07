import random
from typing import Dict, Optional, List
from dataclasses import dataclass
from game_models import SkillData, MonsterDataModel, MonsterDropItemDataModel, ArmorDataModel, WeaponDataModel,ItemDataModel,JobBonusDataModel,StatusFormulaDataModel,GameText,GameSettingDataModel,AreaData,LvAndExpDataModel
from formula_parser import FormulaParser
from typing import Tuple

@dataclass
class BattleCharacter:
    name: str
    jobBonusData: JobBonusDataModel
    level: int
    stats: Dict[str, int]  # hp, mp, attack, defense, etc.
    equipped_weapon: Optional[WeaponDataModel]
    equipped_armor: Optional[ArmorDataModel]
    skills: List[SkillData]
    items: List[ItemDataModel]
    
    def is_alive(self) -> bool:
        return self.stats["hp"] > 0
    
    def use_skill(self, skill: SkillData, target) -> Tuple[str, int]:
        # 實現技能效果
        parser = FormulaParser()
        variables = {
                "attacker_attack": self.stats["attack"] + (self.equipped_weapon.attack if self.equipped_weapon else 0),
                "target_defense": target.stats["defense"] + (target.equipped_armor.defense if target.equipped_armor else 0),
                "skill_power": skill.Damage,  # 直接使用技能資料中的 Damage 值
                "attacker_level": self.level,
                "target_level": target.level,
                "random_factor": random.uniform(0.85, 1.15),
                "base_damage": skill.Damage  # 新增基礎傷害參考值
        }
        parser.set_variables(variables)
        # 假設 skill.Damage 是公式（字串）
        if isinstance(skill.Damage, str):
            damage = int(parser.evaluate(skill.Damage))
        else:
            damage = int(skill.Damage)
        
        target.stats["hp"] -= damage
        self.stats["mp"] -= skill.CastMage
        
        return f"{self.name} 使用 {skill.Name} 對 {target.name} 造成 {damage} 傷害！", damage

class BattleSimulator:
    def __init__(self, game_data):
        self.game_data = game_data
        self.battle_log: List[str] = []
        self.damage_data: List[Dict] = []
        self.skill_usage: Dict[str, int] = {}
    
    def simulate_battle(self, player: BattleCharacter, enemy: BattleCharacter, max_turns=50) -> bool:
        """返回True表示玩家勝利"""
        self.battle_log.clear()
        self.damage_data.clear()
        self.skill_usage = {s.Name: 0 for s in player.skills}
        
        for turn in range(1, max_turns + 1):
            self.battle_log.append(f"=== 第 {turn} 回合 ===")
            
            # 玩家行動
            if player.is_alive():
                skill = self._choose_skill(player)
                log_msg, damage = player.use_skill(skill, enemy)
                self.battle_log.append(log_msg)
                self.damage_data.append({
                    "turn": turn,
                    "attacker": player.name,
                    "target": enemy.name,
                    "skill": skill.Name,
                    "damage": damage
                })
                if skill.Name != '普通攻擊':
                    self.skill_usage[skill.Name] += 1
            
            # 敵人行動
            if enemy.is_alive():
                skill = self._choose_skill(enemy)
                log_msg, damage = enemy.use_skill(skill, player)
                self.battle_log.append(log_msg)
                self.damage_data.append({
                    "turn": turn,
                    "attacker": enemy.name,
                    "target": player.name,
                    "skill": skill.Name,
                    "damage": damage
                })
            
            # 檢查戰鬥結束
            if not enemy.is_alive():
                self.battle_log.append(f"{enemy.name} 被擊敗了！{player.name} 獲勝！")
                return True
            if not player.is_alive():
                self.battle_log.append(f"{player.name} 被擊敗了！{enemy.name} 獲勝！")
                return False
        
        self.battle_log.append("戰鬥超過最大回合數，判定為平局！")
        return False
    
    def _choose_skill(self, character: BattleCharacter) -> SkillData :
        # 簡單的AI選擇技能邏輯
        available_skills = [s for s in character.skills if character.stats["mp"] >= s.CastMage]
        if not available_skills:
            # 沒有MP時使用普通攻擊
            return SkillData(
                    SkillID="NORMAL_ATTACK",
                    Name="普通攻擊",
                    Damage="attacker_attack * 0.8 - target_defense * 0.5",
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