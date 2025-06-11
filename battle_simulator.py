import random
from typing import Dict, Optional, List
from dataclasses import dataclass
from game_models import CharacterClass, Skill, Weapon, Armor, Monster
from formula_parser import FormulaParser

@dataclass
class BattleCharacter:
    name: str
    char_class: CharacterClass
    level: int
    stats: Dict[str, int]  # hp, mp, attack, defense, etc.
    equipped_weapon: Optional[Weapon]
    equipped_armor: Optional[Armor]
    skills: List[Skill]
    items: List[Item]
    
    def is_alive(self) -> bool:
        return self.stats["hp"] > 0
    
    def use_skill(self, skill: Skill, target) -> Tuple[str, int]:
        # 實現技能效果
        parser = FormulaParser()
        variables = {
            "attacker_attack": self.stats["attack"],
            "target_defense": target.stats["defense"],
            "skill_power": 100,  # 示例值，應從技能數據獲取
            "random_factor": random.uniform(0.9, 1.1)
        }
        parser.set_variables(variables)
        damage = int(parser.evaluate(skill.damage_formula))
        
        target.stats["hp"] -= damage
        self.stats["mp"] -= skill.mp_cost
        
        return f"{self.name} 使用 {skill.name} 對 {target.name} 造成 {damage} 傷害！", damage

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
        self.skill_usage = {s.name: 0 for s in player.skills}
        
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
                    "skill": skill.name,
                    "damage": damage
                })
                self.skill_usage[skill.name] += 1
            
            # 敵人行動
            if enemy.is_alive():
                skill = self._choose_skill(enemy)
                log_msg, damage = enemy.use_skill(skill, player)
                self.battle_log.append(log_msg)
                self.damage_data.append({
                    "turn": turn,
                    "attacker": enemy.name,
                    "target": player.name,
                    "skill": skill.name,
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
    
    def _choose_skill(self, character: BattleCharacter) -> Skill:
        # 簡單的AI選擇技能邏輯
        available_skills = [s for s in character.skills if character.stats["mp"] >= s.mp_cost]
        if not available_skills:
            # 沒有MP時使用普通攻擊
            return Skill(id=0, name="普通攻擊", damage_formula="attacker_attack * 0.8 - target_defense * 0.5", 
                        mp_cost=0, cooldown=0, effect="")
        return random.choice(available_skills)
    
    def get_battle_log(self) -> List[str]:
        return self.battle_log
    
    def get_damage_data(self) -> List[Dict]:
        return self.damage_data
    
    def get_skill_usage(self) -> Dict[str, int]:
        return self.skill_usage