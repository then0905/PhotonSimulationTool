import random
from typing import Dict, Optional, List
from dataclasses import dataclass,field
from game_models import GameData, SkillData,SkillOperationData, MonsterDataModel, MonsterDropItemDataModel, ArmorDataModel, WeaponDataModel,ItemDataModel,JobBonusDataModel,StatusFormulaDataModel,GameText,GameSettingDataModel,AreaData,LvAndExpDataModel
from formula_parser import FormulaParser
from typing import Tuple
from commonfunction import CommonFunction
from skill_processor import SkillProcessor
from status_operation import StatusValues

@dataclass
class BattleCharacter:
    #基本資料
    name: str
    jobBonusData: JobBonusDataModel
    level: int
    stats: Dict[str, int]
    basal:StatusValues      #基本屬性數值
    equip:StatusValues      #裝備數值
    effect:StatusValues     #效果影響數值
    equipped_weapon: Optional[WeaponDataModel]
    equipped_armor: Optional[ArmorDataModel]
    skills: List[SkillData]
    items: List[ItemDataModel]
    characterType:bool  #當前攻擊者類型 True:人物 False:怪物
    attackTimer:float = 0   #普通攻擊計時器
    
    #UI物件
    buff_bar: Optional[object] = None     #buff效果提示欄
    debuff_bar: Optional[object] = None  #負面狀態效果提示欄
    passive_bar: Optional[object] = None   #被動效果提示欄
    battle_log = None                      #戰鬥日誌
    
    #動態資料
    skill_cooldowns: Dict[str, float] = field(default_factory=dict)  # skill_id -> remaining_cooldown_time
    buff_skill:  Dict[str, Tuple[SkillData,float]] = field(default_factory=dict)   #運行中的buff效果
    debuff_skill:  Dict[str, Tuple[SkillOperationData,float]] = field(default_factory=dict)    #運行中的負面狀態
    controlled_for_attack:float = 0 #受到控制不得使用普通攻擊類型
    controlled_for_skill:float = 0  #受到控制不得使用技能類型
    attackTimerFunc = None #儲存普攻計時任務
    hp_recovery_time:float = 0 #血量自然恢復間隔計時
    mp_recovery_time:float = 0 #魔力自然恢復間隔計時
    update_hp_mp = None    #用來儲存更新雙方血量魔力的匿名方法


    def action_check(self,skill:SkillData)->bool:
        """
        攻擊指令許可確定
        """
        if(skill.Name == "普通攻擊"):
            return self.stats["HP"] > 0 and self.controlled_for_attack <=0
        else:
            return self.stats["HP"] > 0 and self.controlled_for_skill <=0

    def is_alive(self) -> bool:
        return self.stats["HP"] > 0

    def pass_time(self, dt: float):
        """
        獨立計時器
        """
        # 技能冷卻遞減
        for skill_id in list(self.skill_cooldowns):
            if self.skill_cooldowns[skill_id] > 0:
                self.skill_cooldowns[skill_id] = max(0, self.skill_cooldowns[skill_id] - dt)
                if self.skill_cooldowns[skill_id] == 0:
                    del self.skill_cooldowns[skill_id]
       
        # buff狀態遞減
        for buff in list(self.buff_skill):
             skillData,skillDuration =  self.buff_skill[buff]
             skillDuration = max(0, skillDuration - dt)
             self.buff_skill[buff] = (skillData,skillDuration)
             if(skillDuration == 0):
                for op in skillData.SkillOperationDataList:
                    self.SkillEffectStatusOperation(op.InfluenceStatus,(op.AddType == "Rate"),-1*op.EffectValue)
                    del self.buff_skill[buff]
                    self.buff_bar.remove_effect(buff)

        #負面狀態遞減
        for debuff in list(self.debuff_skill):
            op,debuffDuration =  self.debuff_skill[debuff]
            debuffDuration = max(0, debuffDuration - dt)
            self.debuff_skill[debuff] = (op,debuffDuration)
            if(debuffDuration == 0):
                log,dmg,cd = SkillProcessor.status_effect_end(op , self)
                self.battle_log.append(log)
                del self.debuff_skill[debuff]
                self.debuff_bar.remove_effect(debuff)
        
        # 血量自然恢復計時
        if("HP_Recovery" in self.stats):            
            if(self.hp_recovery_time < GameData.Instance.GameSettingDic["HpRecoverySec"].GameSettingValue):
                self.hp_recovery_time+=dt
            else:
                self.hp_recovery_time = 0
                self.stats["HP"]+=self.stats["HP_Recovery"]
                self.update_hp_mp()
                self.battle_log.append(f"自然回復生命 讓<color=#00ffdc>{self.name}</color> 恢復了<color=#ff0000>{self.stats["HP_Recovery"]}</color> 生命")

        # 魔力自然恢復計時
        if("MP_Recovery" in self.stats):            
            if(self.mp_recovery_time < GameData.Instance.GameSettingDic["MpRecoverySec"].GameSettingValue):
                self.hp_recovery_time+=dt
            else:
                self.mp_recovery_time = 0
                self.stats["MP"]+=self.stats["MP_Recovery"]
                self.update_hp_mp()
                self.battle_log.append(f"自然回復魔力 讓<color=#00ffdc>{self.name}</color> 恢復了<color=#ff0000>{self.stats["MP_Recovery"]}</color> 魔力")

    def PassTimeControll(self,passtime:float):
        """
        處理經過時間
        """
        if(controlled_for_attack!=0):
            controlled_for_attack = CommonFunction.clamp((controlled_for_attack-passtime),0,controlled_for_attack);
        if(controlled_for_skill!=0):
            controlled_for_skill = CommonFunction.clamp((controlled_for_skill-passtime),0,controlled_for_skill);
    
    def run_passive_skill(self):
        """
        運行被動技能
        """
        passive_skills =  [s for s in self.skills if s.Characteristic == False]
        if(passive_skills is not None):
            for skill in passive_skills:
                SkillProcessor._execute_skill_operation(skill,self,self)
                self.passive_bar.add_effect(skill)

    def add_buff_effect(self,skillData:SkillData):
        """
        增加buff效果
        """
        for op in skillData.SkillOperationDataList:
            self.SkillEffectStatusOperation(op.InfluenceStatus,(op.AddType == "Rate"),op.EffectValue)
            
        self.buff_bar.add_effect(skillData)
        self.buff_skill[skillData.SkillID] = (skillData,skillData.SkillOperationDataList[0].EffectDurationTime)
    
    def add_debuff_effect(self,op:SkillOperationData):
        """
        增加負面效果(含 控制狀態)
        """
        self.debuff_bar.add_debuff(op.InfluenceStatus)
        self.debuff_skill[op.InfluenceStatus] = op,op.EffectDurationTime

    def CrowdControlCalculator(self,op: SkillOperationData,value :int):
        """
        控制效果計算
        """
        match(op.InfluenceStatus):
            case "Stun":
                self.controlled_for_skill+=value
                self.controlled_for_attack+=value
            case "Taunt":
                self.controlled_for_attack+=value

    #region 戰鬥數值 計算

    def HitCalculator(self, skill: SkillData, target) -> Tuple[str, int, float]:
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
    
    def BlockCalculator(self, skill: SkillData, target)-> Tuple[str, int, float]:
        """
        格檔計算
        """
        is_block = random.randint(0,100)    
        if(is_block <= self.stats["BlockRate"]):
            return f" <color=#00ffdc>{self.name}</color> 使用 <color=#ff9300>{CommonFunction.get_text(skill.Name)}</color> 但被格檔了！", 0, self.attackTimer
        else:
            return self.CrtCalculator(skill,target)
            
    def CrtCalculator(self, skill: SkillData, target)-> Tuple[str, int, float]:
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
            
    def AttackCalculator(self, skill: SkillData, target,is_Crt:bool) -> Tuple[str, int, float]:
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
            damage = round(variables["attacker_attack"]*skill.Damage*1.5)+self.stats["CrtDamage"]
        else:
            damage = round(variables["attacker_attack"]*skill.Damage)

        finalDamage = CommonFunction.clamp(round(damage * (1 - defenseRatio)) - target.stats["DamageReduction"],0,round(damage * (1 - defenseRatio)) - target.stats["DamageReduction"])
        print(f"攻擊對象:{self.characterType}，攻擊者傷害:{damage}，防禦減免{defenseRatio}，最後傷害{finalDamage}")
        
        target.stats["HP"] -= finalDamage
        self.stats["MP"] -= skill.CastMage
        
        color_code = '#ffba01' if is_Crt else '#ff0000'
        
        return f" <color=#00ffdc>{self.name}</color> 使用 <color=#ff9300>{CommonFunction.get_text(skill.Name)}</color> 對  <color=#83ff00>{target.name}</color> 造成 <color={color_code}>{finalDamage}</color> 傷害！", finalDamage, self.attackTimer

    #endregion

    def SkillEffectStatusOperation(self, stateType:str, isRate:bool, value:float):
        """
        技能效果運算
        """
        match(stateType):
            case "MeleeATK":
                self.effect.MeleeATK += round(self.basal.MeleeATK * value) if isRate else round(value)
                print(f"basal.MeleeATK:{self.basal.MeleeATK} valur:{value} processor{self.basal.MeleeATK * value}  final to int {round(self.basal.MeleeATK * value)}")
            case "RemoteATK":
                self.effect.RemoteATK += round(self.basal.RemoteATK * value) if isRate else round(value)
            case "MageATK":
                self.effect.MageATK += round(self.basal.MageATK * value) if isRate else round(value)    
            case "MaxHP":
                self.effect.MaxHP += round(self.basal.MaxHP * value) if isRate else round(value)
                print(f"basal.MaxHP:{self.basal.MaxHP} valur:{value} processor{self.basal.MaxHP * value}  final to int {round(self.basal.MaxHP * value)}")
            case "MaxMP":
                self.effect.MaxMP += round(self.basal.MaxMP * value) if isRate else round(value)
            case "DEF":
                self.effect.DEF += round(self.basal.DEF * value) if isRate else round(value)
            case "Avoid":
                self.effect.Avoid += round(self.basal.Avoid * value) if isRate else round(value)
            case "MeleeHit":
                self.effect.MeleeHit += round(self.basal.MeleeHit * value) if isRate else round(value)
            case "RemoteHit":
                self.effect.RemoteHit += round(self.basal.RemoteHit * value) if isRate else round(value)
            case "MageHit":
                self.effect.MageHit += round(self.basal.MageHit * value) if isRate else round(value)
            case "MDEF":
                self.effect.MDEF += round(self.basal.MDEF * value) if isRate else round(value)
            case "BlockRate":
                self.effect.BlockRate += round(self.basal.BlockRate * value) if isRate else round(value)
            case "DamageReduction":
                self.effect.DamageReduction += round(self.basal.DamageReduction * value) if isRate else round(value)
            case "ElementDamageIncrease":
                self.effect.ElementDamageIncrease += round(self.basal.ElementDamageIncrease * value) if isRate else round(value)
            case "ElementDamageReduction":
                self.effect.ElementDamageReduction += round(self.basal.ElementDamageReduction * value) if isRate else round(value)
            case "HP_Recovery":
                self.effect.HP_Recovery += round(self.basal.HP_Recovery * value) if isRate else round(value)
            case "MP_Recovery":
                self.effect.MP_Recovery += round(self.basal.MP_Recovery * value) if isRate else round(value)
            case "Crt":
                self.effect.Crt += round(self.basal.Crt * value) if isRate else round(value)
            case "CrtResistance":
                self.effect.CrtResistance += round(self.basal.CrtResistance * value) if isRate else round(value)
            case "CrtDamage":
                self.effect.CrtDamage += round(self.basal.CrtDamage * value) if isRate else round(value)
            case "BlockRate":
                self.effect.BlockRate += round(self.basal.BlockRate * value) if isRate else round(value)
            case "Speed":
                self.effect.Speed += round(1 * value) if isRate else round(value)
            case "AS":
                self.effect.AS += round(self.basal.AS * value) if isRate else round(value)
            case "DisorderResistance":
                self.effect.DisorderResistance += round(self.basal.DisorderResistance * value) if isRate else round(value)
            case "ATK":
                self.effect.MeleeATK += round(self.basal.MeleeATK * value) if isRate else round(value)
                self.effect.RemoteATK += round(self.basal.RemoteATK * value) if isRate else round(value)
                self.effect.MageATK += round(self.basal.MageATK * value) if isRate else round(value)
        self.stats =  {  # 計算後的屬性值
            "MaxHP": self.basal.MaxHP + self.equip.MaxHP + self.effect.MaxHP,
            "HP": self.basal.MaxHP + self.equip.MaxHP + self.effect.MaxHP,
            "MaxMP": self.basal.MaxMP + self.equip.MaxMP + self.effect.MaxMP,
            "MP": self.basal.MaxMP + self.equip.MaxMP + self.effect.MaxMP,
            "MeleeATK": self.basal.MeleeATK + self.equip.MeleeATK+ self.effect.MeleeATK,
            "RemoteATK": self.basal.RemoteATK + self.equip.RemoteATK+ self.effect.RemoteATK,
            "MageATK": self.basal.MageATK + self.equip.MageATK+ self.effect.MageATK,
            "DEF": self.basal.DEF + self.equip.DEF+ self.effect.DEF,
            "Avoid": self.basal.Avoid + self.equip.Avoid+ self.effect.Avoid,
            "MeleeHit": self.basal.MeleeHit + self.equip.MeleeHit+ self.effect.MeleeHit,
            "RemoteHit": self.basal.RemoteHit + self.equip.RemoteHit+ self.effect.RemoteHit,
            "MageHit": self.basal.MageHit + self.equip.MageHit+ self.effect.MageHit,
            "MDEF": self.basal.MDEF + self.equip.MDEF+ self.effect.MDEF,
            "Speed": self.basal.Speed + self.equip.Speed+ self.effect.Speed,
            "AS": self.basal.AS + self.equip.AS+ self.effect.AS,
            "DamageReduction": self.basal.DamageReduction + self.equip.DamageReduction+ self.effect.DamageReduction,
            "ElementDamageIncrease": self.basal.ElementDamageIncrease
            + self.equip.ElementDamageIncrease+ self.effect.ElementDamageIncrease,
            "ElementDamageReduction": self.basal.ElementDamageReduction
            + self.equip.ElementDamageReduction+ self.effect.ElementDamageReduction,
            "HP_Recovery": self.basal.HP_Recovery + self.equip.HP_Recovery+ self.effect.HP_Recovery,
            "MP_Recovery": self.basal.MP_Recovery + self.equip.MP_Recovery+ self.effect.MP_Recovery,
            "Crt": self.basal.Crt+ self.equip.Crt+ self.effect.Crt,
            "CrtResistance": self.basal.CrtResistance+ self.equip.CrtResistance+ self.effect.CrtResistance,
            "CrtDamage": self.basal.CrtDamage+ self.equip.CrtDamage+ self.effect.CrtDamage,
            "BlockRate": self.basal.BlockRate+ self.equip.BlockRate+ self.effect.BlockRate,
            "DisorderResistance": self.basal.DisorderResistance+ self.equip.DisorderResistance+ self.effect.DisorderResistance,
            "DamageReduction": self.basal.DamageReduction+ self.equip.DamageReduction+ self.effect.DamageReduction,
            }
        


class BattleSimulator:
    def __init__(self, game_data,gui):
        self.game_data = game_data
        self.gui = gui
        self.battle_log: List[str] = []
        self.damage_data: List[Dict] = []
        self.skill_usage: Dict[str, int] = {}
        self.update_hp_mp = None    #用來儲存更新雙方血量魔力的匿名方法

    def battle_tick(self,player,enemy):
        """
        啟動各自計時器
        """
        dt = 0.1  # 每 0.1 秒刷新一次
        player.pass_time(dt)
        enemy.pass_time(dt)
        
        self.gui.root.after(int(dt*1000), lambda:self.battle_tick(player,enemy))

    def attack_loop(self, attacker: BattleCharacter, target):
        """獨立的攻擊計時器迴圈"""
        
        if attacker.is_alive() and target.is_alive():
            skill = self._choose_skill(attacker)
            
            if attacker.action_check(skill):
                log_msg, damage, attack_timer = SkillProcessor._execute_skill_operation(skill,attacker,target)
                self.battle_log.append(log_msg)
                
                if(skill.SkillID == "NORMAL_ATTACK"):
                    
                    self.battle_log.append(f"[ <color=#00ffdc>{attacker.name}</color> 進入<color=#ff0000>普攻</color>計時 {attack_timer:.2f} 秒 ]")
                    self.gui.display_battle_log(self.get_battle_log());
                    attacker.attackTimerFunc = self.gui.root.after(int(attack_timer*1000) ,lambda: self.attack_loop(attacker, target))
                else:
                    
                    self.battle_log.append(f"[ <color=#00ffdc>{attacker.name}</color> 施放了 <color=#ff0000>{CommonFunction.get_text(skill.Name)}</color> 需等待 {1 if skill.Type == "Buff" else 1.8} 秒 ]")
                    self.gui.display_battle_log(self.get_battle_log());
                    attacker.skill_cooldowns[skill.SkillID] = skill.CD
                    attacker.attackTimerFunc = self.gui.root.after(1000 if skill.Type == "Buff" else 1800 ,lambda: self.attack_loop(attacker, target))
                    
                #更新雙方血量魔力
                self.update_hp_mp()
                
            else:
                attacker.attackTimerFunc = self.gui.root.after(100, lambda: self.attack_loop(attacker, target))
                
        else:
            if(attacker.attackTimerFunc is not None):
                self.gui.root.after_cancel(attacker.attackTimerFunc)
                self.check_battle_result(attacker,target)
                
    def simulate_battle(self, player: BattleCharacter, enemy: BattleCharacter):
        """開啟戰鬥模擬"""
        self.battle_log.clear()
        self.damage_data.clear()
        self.skill_usage = {s.Name: 0 for s in player.skills}
        
        player.run_passive_skill()
        enemy.run_passive_skill()

        #匿名方法 更新雙方血量魔力
        def update_hp_mp():
            self.gui.player_hp_bar.set_value(player.stats["HP"],player.stats["MaxHP"])
            self.gui.player_mp_bar.set_value(player.stats["MP"],player.stats["MaxMP"])
            self.gui.enemy_hp_bar.set_value(enemy.stats["HP"],enemy.stats["MaxHP"])
            self.gui.enemy_mp_bar.set_value(enemy.stats["MP"],enemy.stats["MaxMP"])        
        self.update_hp_mp = update_hp_mp
        
        player.update_hp_mp = update_hp_mp
        enemy.update_hp_mp = update_hp_mp

        #初始化雙方血量魔力
        self.update_hp_mp()
        player.battle_log = self.battle_log
        enemy.battle_log = self.battle_log
        
        #雙方獨立計時器啟動
        self.battle_tick(player,enemy)
        
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
        
    def _choose_skill(self, character: BattleCharacter) -> SkillData :
        """
        選擇技能
        """
        # 簡單的AI選擇技能邏輯
        current_active_buff = [s for s in (character.buff_skill or {}) ]     #當前生效的buff效果
        current_cooldown_buff = [s for s in (character.skill_cooldowns or {})]     #當前進入冷卻時間的技能
        
        available_skills = [s for s in character.skills if s.Characteristic is True and character.stats["MP"] >= s.CastMage and s.SkillID not in current_active_buff and s.SkillID not in current_cooldown_buff]
        if not available_skills:
            # 沒有MP時使用普通攻擊
            return SkillData(
                    SkillID="NORMAL_ATTACK",
                    Name="普通攻擊",
                    Damage=1,
                    CastMage=0,
                     # 其他必要參數...
            )
        # 使用 sorted() 進行排序，Type == "Buff" 的技能優先
        # key 函數返回 (priority, skill)，其中 priority 為 0 表示 Buff 技能（最高優先級），1 表示其他技能
        sorted_skills = sorted(available_skills, key=lambda skill: (0 if skill.Type == "Buff" else 1, skill.SkillID))
    
        return random.choice(sorted_skills[:3] if len(sorted_skills) > 3 else sorted_skills)  # 從前3個技能中隨機選擇

    def get_battle_log(self) -> List[str]:
        return self.battle_log
    
    def get_damage_data(self) -> List[Dict]:
        return self.damage_data
    
    def get_skill_usage(self) -> Dict[str, int]:
        return self.skill_usage