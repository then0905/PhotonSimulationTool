import random
from typing import Dict, Optional, List
from dataclasses import dataclass,field
from game_models import GameData, ItemsDic, SkillData,SkillOperationData, MonsterDataModel, MonsterDropItemDataModel, ArmorDataModel, WeaponDataModel,ItemDataModel,JobBonusDataModel,StatusFormulaDataModel,GameText,GameSettingDataModel,AreaData,LvAndExpDataModel
from formula_parser import FormulaParser
from typing import Tuple
from commonfunction import CommonFunction
from skill_processor import SkillProcessor
from status_operation import StatusValues
from AICombatAction import ai_action
from commontool import Event
import os

@dataclass
class BattleCharacter:
    #基本資料
    name: str
    jobBonusData: JobBonusDataModel
    ai_id: str
    level: int
    stats: Dict[str, int]
    basal:StatusValues      #基本屬性數值
    equip:StatusValues      #裝備數值
    effect:StatusValues     #效果影響數值
    equipped_weapon: Optional[WeaponDataModel]
    equipped_armor: Optional[ArmorDataModel]
    skills: List[SkillData]
    items: List[Tuple[ItemDataModel,int]]
    characterType:bool  #當前攻擊者類型 True:人物 False:怪物
    attackTimer:float = 0   #普通攻擊計時器
    
    #UI物件
    buff_bar: Optional[object] = None     #buff效果提示欄
    debuff_bar: Optional[object] = None  #負面狀態效果提示欄
    passive_bar: Optional[object] = None   #被動效果提示欄
    battle_log = None                      #戰鬥日誌
    item_manager: Optional[object] = None   #道具管理器
    ai: "ai_action" = field(init=False)     # Q learning AI

    #動態資料
    skill_cooldowns: Dict[str, float] = field(default_factory=dict)  # skill_id -> remaining_cooldown_time
    item_cooldowns: Dict[str, float] = field(default_factory=dict)  # item_id -> remaining_cooldown_time
    buff_skill:  Dict[str, Tuple[SkillData,float]] = field(default_factory=dict)   #運行中的buff效果
    buff_item:  Dict[str, Tuple[ItemDataModel,float]] = field(default_factory=dict)   #運行中的buff效果
    debuff_skill:  Dict[str, Tuple[SkillOperationData,float]] = field(default_factory=dict)    #運行中的負面狀態
    controlled_for_attack:float = 0 #受到控制不得使用普通攻擊類型
    controlled_for_skill:float = 0  #受到控制不得使用技能類型
    attackTimerFunc = None #儲存普攻計時任務
    hp_recovery_time:float = 0 #血量自然恢復間隔計時
    mp_recovery_time:float = 0 #魔力自然恢復間隔計時
    update_hp_mp = None    #用來儲存更新雙方血量魔力的匿名方法
    additive_buff_event: Event = field(default_factory=Event, init=False, repr=False) #滿足條件的Buff持續疊加的事件
    additive_buff_time = 0 #滿足條件的Buff 作用的間隔時間
    additive_debuff_event: Event = field(default_factory=Event, init=False, repr=False) #滿足條件的DeBuff持續疊加的事件
    additive_debuff_time = 0 #滿足條件的DeBuff 作用的間隔時間

    def __post_init__(self):
        # 在物件建立後，才初始化 AI
        self.ai = ai_action(self.ai_id, self.skills, self.items)

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
        for item_id in list(self.item_cooldowns):
            if self.item_cooldowns[item_id] > 0:
                self.item_cooldowns[item_id] = max(0, self.skill_cooldowns[item_id] - dt)
                if self.item_cooldowns[item_id] == 0:
                    del self.item_cooldowns[item_id]       

        # buff狀態遞減
        #技能Buff時間遞減
        for buff in list(self.buff_skill):
             skillData,skillDuration =  self.buff_skill[buff]
             skillDuration = max(0, skillDuration - dt)
             self.buff_skill[buff] = (skillData,skillDuration)
             if(skillDuration == 0):
                stack = self.buff_bar.get_effect_stack(buff)
                for op in skillData.SkillOperationDataList:
                    self.SkillEffectStatusOperation(op.InfluenceStatus,(op.AddType == "Rate"),-1*op.EffectValue*stack)
                    self.buff_skill.pop(buff, None)
                    self.buff_bar.remove_effect(buff)
        for buff in list(self.buff_item):
            try:
             itemData,itemDuration =  self.buff_item[buff]
             itemDuration = max(0, itemDuration - dt)
             self.buff_skill[buff] = (itemData,itemDuration)
             if(itemDuration == 0):
                stack = self.buff_bar.get_effect_stack(buff)
                for op in itemData.ItemEffectDataList:
                    self.SkillEffectStatusOperation(op.InfluenceStatus,(op.AddType == "Rate"),-1*op.EffectValue*stack)
                    self.buff_skill.pop(buff, None)
                    self.buff_bar.remove_effect(buff)

            except KeyError:
                print(f"Buff錯誤{buff}")
        #負面狀態遞減
        for debuff in list(self.debuff_skill):
            op,debuffDuration =  self.debuff_skill[debuff]
            debuffDuration = max(0, debuffDuration - dt)
            self.debuff_skill[debuff] = (op,debuffDuration)
            if(debuffDuration == 0):
                log,dmg,cd = SkillProcessor.status_skill_effect_end(op , self)
                self.battle_log.append(log)
                del self.debuff_skill[debuff]
                self.debuff_bar.remove_effect(debuff)
        
        # 血量自然恢復計時
        if("HP_Recovery" in self.stats):            
            if(self.hp_recovery_time < GameData.Instance.GameSettingDic["HpRecoverySec"].GameSettingValue):
                self.hp_recovery_time+=dt
            else:
                self.hp_recovery_time = 0
                self.stats["HP"] = CommonFunction.clamp(self.stats["HP"]+self.stats["HP_Recovery"],0,self.stats["MaxHP"])
                self.update_hp_mp()
                self.battle_log.append(CommonFunction.battlelog_text_processor({
                "caster_text":self.name,
                "caster_color":"#00ffdc",
                "descript_text":self.stats["HP_Recovery"],
                "descript_color":"#ff0000",
        },"naturalHpRecovery"))
                
        # 魔力自然恢復計時
        if("MP_Recovery" in self.stats):            
            if(self.mp_recovery_time < GameData.Instance.GameSettingDic["MpRecoverySec"].GameSettingValue):
                self.mp_recovery_time+=dt
            else:
                self.mp_recovery_time = 0
                self.stats["MP"] = CommonFunction.clamp(self.stats["MP"]+self.stats["MP_Recovery"],0,self.stats["MaxMP"])
                self.update_hp_mp()
                self.battle_log.append(CommonFunction.battlelog_text_processor({
                "caster_text":self.name,
                "caster_color":"#00ffdc",
                "descript_text":self.stats["MP_Recovery"],
                "descript_color":"#ff0000",
        },"naturalMpRecovery"))
                
        #持續疊加的Buff
        if(self.additive_buff_time < 0.25):
            self.additive_buff_time += dt
        else:
            self.additive_buff_time=0
            self.additive_buff_event()

        #持續疊加的Debuff
        if (self.additive_debuff_time < 0.25):
            self.additive_debuff_time += dt
        else:
            self.additive_debuff_time = 0
            self.additive_debuff_event()

    def use_item_id(self,itemid)-> Tuple[str, int, float]:
        for idx, (item, count) in enumerate(self.items):
            if count > 0 and item.CodeID not in self.item_cooldowns and itemid == item.CodeID:
                # 執行道具效果，只傳 item
                for temp in  SkillProcessor.execute_item_operation(item, self, self):
                    log_msg, damage, attack_timer =temp
            
                    # 使用後扣除數量
                    count -= 1
                    self.item_manager.consume_item(itemid)
                    if count <= 0:
                        # 數量為0，刪除這個道具
                        self.items.pop(idx)
                    else:
                        # 更新數量
                        self.items[idx] = (item, count)
            
                    return log_msg, damage, attack_timer  # 回傳執行結果

    def run_passive_skill(self):
        """
        運行被動技能
        """
        passive_skills =  [s for s in self.skills if s.Characteristic == False]
        if(passive_skills is not None):
            for skill in passive_skills:
                SkillProcessor._execute_skill_operation(skill,self,self)
                self.passive_bar.add_skill_effect(skill)

    def add_skill_buff_effect(self,skillData:SkillData,op):
        """
        增加技能buff效果
        """
        self.SkillEffectStatusOperation(op.InfluenceStatus,(op.AddType == "Rate"),op.EffectValue)
        self.buff_bar.add_skill_effect(skillData)
        self.buff_skill[skillData.SkillID] = (skillData,skillData.SkillOperationDataList[0].EffectDurationTime)

    def add_skill_addtive_effect(self,skillData:SkillData,op,stackCount:int):
        """
        增加疊加型效果
        """
        #效果欄增加資料
        self.buff_bar.add_skill_effect(skillData,stackCount)
        #重刷效果欄持續時間
        self.buff_skill[skillData.SkillID] = (skillData, skillData.SkillOperationDataList[0].EffectDurationTime)
        if(self.buff_bar.get_effect_stack(skillData.SkillID) >= op.Bonus):
            self.SkillEffectStatusOperation(op.InfluenceStatus, (op.AddType == "Rate"), op.EffectValue)

    def add_item_buff_effect(self,op,itemData:ItemDataModel):
        """
        增加道具buff效果
        """

        self.SkillEffectStatusOperation(op.InfluenceStatus,(op.AddType == "Rate"),op.EffectValue)
            
        self.buff_bar.add_item_effect(itemData)
        self.buff_item[itemData.CodeID] = (itemData,itemData.ItemEffectDataList[0].EffectDurationTime)
    
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

    def processRecovery(self,op, caster, target)-> Tuple[str, int, float]:
        """
        處理任何恢復效果 
        """
        maxValue = "MaxMP" if op.InfluenceStatus == "MP" else "MaxHP";

        target.stats[op.InfluenceStatus] = CommonFunction.clamp(target.stats[op.InfluenceStatus]+ op.EffectValue, target.stats[op.InfluenceStatus],target.stats[maxValue])

        self.update_hp_mp()
        color_code = "#2945FF" if op.InfluenceStatus == "MP" else "#ff0000";
        recovery_type = "魔力" if op.InfluenceStatus == "MP" else "血量";
        return CommonFunction.battlelog_text_processor({
                "caster_text":caster.name,
                "caster_color":"#00ffdc",
                "descript_text":CommonFunction.get_text("TM_"+op.CodeID+"_Name"),
                "descript_color":"#ff9300",
                "target_text":target.name,
                "target_color":"#83ff00",
        },"effectRecovery",f"<color={color_code}>{op.EffectValue} {recovery_type} </color>"), op.EffectValue, 0


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
            return CommonFunction.battlelog_text_processor({
                "caster_text":self.name,
                "caster_color":"#636363",
                "caster_size":12,
                "descript_text":CommonFunction.get_text(skill.Name),
                "descript_color":"#ff9300",
        },"miss"), 0, self.attackTimer
    
    def BlockCalculator(self, skill: SkillData, target)-> Tuple[str, int, float]:
        """
        格檔計算
        """
        is_block = random.randint(0,100)    
        if(is_block <= self.stats["BlockRate"]):
            return CommonFunction.battlelog_text_processor({
                "caster_text":self.name,
                "caster_color":"#636363",
                "caster_size":12,
                "descript_text":CommonFunction.get_text(skill.Name),
                "descript_color":"#ff9300",
        },"block"), 0, self.attackTimer
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
        # print(f"技能傷害倍率:{skill.Damage}")
        #計算傷害
        if is_Crt:
            damage = round(variables["attacker_attack"]*skill.Damage*1.5)+self.stats["CrtDamage"]
        else:
            damage = round(variables["attacker_attack"]*skill.Damage)

        finalDamage = CommonFunction.clamp(round(damage * (1 - defenseRatio)) - target.stats["DamageReduction"],0,round(damage * (1 - defenseRatio)) - target.stats["DamageReduction"])
        # print(f"攻擊對象:{self.characterType}，攻擊者傷害:{damage}，防禦減免{defenseRatio}，最後傷害{finalDamage}")
        
        target.stats["HP"] -= finalDamage
        
        color_code = f'<color=#ffd600><size=13><b>{finalDamage}</size></color></b>' if is_Crt else f'<color=#ff0000><size=11>{finalDamage}</size></color>'
        return CommonFunction.battlelog_text_processor({
                "caster_text":self.name,
                "caster_color":"#636363",
                "caster_size":12,
                "descript_text":CommonFunction.get_text(skill.Name),
                "descript_color":"#910000",
                "target_text":target.name,
                "target_color":"#363636"
               },"damage",color_code), finalDamage, self.attackTimer


    #endregion

    def SkillEffectStatusOperation(self, stateType:str, isRate:bool, value:float):
        """
        技能效果運算
        """
        self.tempHp = 0
        self.tempMp = 0
        match(stateType):
            case "MeleeATK":
                self.effect.MeleeATK += round(self.basal.MeleeATK * value) if isRate else round(value)
                # print(f"basal.MeleeATK:{self.basal.MeleeATK} valur:{value} processor{self.basal.MeleeATK * value}  final to int {round(self.basal.MeleeATK * value)}")
            case "RemoteATK":
                self.effect.RemoteATK += round(self.basal.RemoteATK * value) if isRate else round(value)
            case "MageATK":
                self.effect.MageATK += round(self.basal.MageATK * value) if isRate else round(value)    
            case "MaxHP":
                #暫存 此次buff影響的數值(效果提升的值 當前生命會跟著提升)
                self.tempHp = round(self.basal.MaxHP * value) if isRate else round(value)

                self.effect.MaxHP += round(self.basal.MaxHP * value) if isRate else round(value)
                # print(f"basal.MaxHP:{self.basal.MaxHP} valur:{value} processor{self.basal.MaxHP * value}  final to int {round(self.basal.MaxHP * value)}")
            case "MaxMP":
                #暫存 此次buff影響的數值(效果提升的值 當前魔力會跟著提升)
                self.tempMp = round(self.basal.MaxMP * value) if isRate else round(value)

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
        self.stats["MaxHP"] =self.basal.MaxHP + self.equip.MaxHP + self.effect.MaxHP
        self.stats["MaxMP"] =self.basal.MaxMP + self.equip.MaxMP + self.effect.MaxMP
        self.stats["HP"] =self.stats["HP"] + self.tempHp
        self.stats["MP"] =self.stats["MP"] + self.tempMp
        self.stats["MeleeATK"] =self.basal.MeleeATK + self.equip.MeleeATK + self.effect.MeleeATK
        self.stats["RemoteATK"] =self.basal.RemoteATK + self.equip.RemoteATK + self.effect.RemoteATK
        self.stats["MageATK"] =self.basal.MageATK + self.equip.MageATK + self.effect.MageATK
        self.stats["DEF"] =self.basal.DEF + self.equip.DEF + self.effect.DEF
        self.stats["Avoid"] =self.basal.Avoid + self.equip.Avoid + self.effect.Avoid
        self.stats["MeleeHit"] =self.basal.MeleeHit + self.equip.MeleeHit + self.effect.MeleeHit
        self.stats["RemoteHit"] =self.basal.RemoteHit + self.equip.RemoteHit + self.effect.RemoteHit
        self.stats["MageHit"] =self.basal.MageHit + self.equip.MageHit + self.effect.MageHit
        self.stats["MDEF"] =self.basal.MDEF + self.equip.MDEF + self.effect.MDEF
        self.stats["Speed"] =self.basal.Speed + self.equip.Speed + self.effect.Speed
        self.stats["AS"] =self.basal.AS + self.equip.AS + self.effect.AS
        self.stats["DamageReduction"] =self.basal.DamageReduction + self.equip.DamageReduction + self.effect.DamageReduction
        self.stats["ElementDamageIncrease"] =self.basal.ElementDamageIncrease + self.equip.ElementDamageIncrease + self.effect.ElementDamageIncrease
        self.stats["ElementDamageReduction"] =self.basal.ElementDamageReduction + self.equip.ElementDamageReduction + self.effect.ElementDamageReduction
        self.stats["HP_Recovery"] =self.basal.HP_Recovery + self.equip.HP_Recovery + self.effect.HP_Recovery
        self.stats["MP_Recovery"] =self.basal.MP_Recovery + self.equip.MP_Recovery + self.effect.MP_Recovery
        self.stats["Crt"] =self.basal.Crt + self.equip.Crt + self.effect.Crt
        self.stats["CrtResistance"] =self.basal.CrtResistance + self.equip.CrtResistance + self.effect.CrtResistance
        self.stats["CrtDamage"] =self.basal.CrtDamage + self.equip.CrtDamage + self.effect.CrtDamage
        self.stats["BlockRate"] =self.basal.BlockRate + self.equip.BlockRate + self.effect.BlockRate
        self.stats["DisorderResistance"] =self.basal.DisorderResistance + self.equip.DisorderResistance + self.effect.DisorderResistance
        self.stats["DamageReduction"] =self.basal.DamageReduction + self.equip.DamageReduction + self.effect.DamageReduction

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

        # 暫停不執行並Delay
        if(os.environ.get("PAUSED") == "1"):
            self.gui.root.after(int(dt * 100), lambda: self.battle_tick(player, enemy))
            return

        player.pass_time(dt)
        enemy.pass_time(dt)
        self.gui.root.after(int(dt*1000), lambda:self.battle_tick(player,enemy))

    def attack_loop(self, attacker: BattleCharacter, target):
        """獨立的攻擊計時器迴圈"""

        # 暫停不執行並Delay
        if (os.environ.get("PAUSED") == "1"):
            self.gui.root.after(
                100, lambda: self.attack_loop(attacker, target)
            )
            return

        if attacker.is_alive() and target.is_alive():
            action_id, state = attacker.ai.choose_action(attacker, target)
            self.ai_choose_result(attacker.ai,state,attacker,target,action_id)

    def ai_choose_result(self,ai,state,attacker: BattleCharacter, target:BattleCharacter,result:str):
        """
        AI 選擇&結果
        """
        reward = 0
        total_attack_timer = 0
        match(result):
            case "NORMAL_ATTACK":
                normal_attack =SkillData(
                    SkillID="NORMAL_ATTACK",
                    Name="普通攻擊",
                    Damage=1,
                    CastMage=0,
                     # 其他必要參數...
                )
                if attacker.action_check(normal_attack):
                    for temp in SkillProcessor._execute_skill_operation(normal_attack,attacker,target,self.gui):
                        log_msg, damage, attack_timer = temp
                        self.battle_log.append(log_msg)
                        reward += damage
                        total_attack_timer += attack_timer
                        self.battle_log.append( CommonFunction.battlelog_text_processor({
                "caster_text":attacker.name,
                "caster_color":"#636363",
                "caster_size":12,
                "descript_text":"普攻",
                "descript_color":"#ff0000",
               },"normalAttckTimer",f"{total_attack_timer:.2f}"))
                else:
                    self.gui.root.after(
                        100, lambda: self.attack_loop(attacker, target)
                    )
                    return
            #道具
            case str() if result.startswith("USE_ITEM:"):
                log_msg, damage, attack_timer = attacker.use_item_id(result.replace("USE_ITEM:",""))
                self.battle_log.append(log_msg)
                reward += damage
                total_attack_timer += attack_timer
            #施放技能
            case _:
                skill =  next(s for s in attacker.skills if s.SkillID == result)
                if attacker.action_check(skill):
                    print(f"{attacker.name} 使用 ：{CommonFunction.get_text(skill.Name)} ({skill.SkillID}) 原本魔力為：{attacker.stats["MP"]} 消耗魔力為：{skill.CastMage}")
                    attacker.stats["MP"] -= skill.CastMage
                    for temp in SkillProcessor._execute_skill_operation(skill,attacker,target,self.gui):
                        log_msg, damage, attack_timer = temp
                        self.battle_log.append(log_msg)
                        self.battle_log.append( CommonFunction.battlelog_text_processor({
                "caster_text":attacker.name,
                "caster_color":"#636363",
                "caster_size":12,
                "descript_text":CommonFunction.get_text(skill.Name),
                "descript_color":"#ff0000",
               },"skillTimer",f"{1 if skill.Type == "Buff" else 1.8}"))
                        attacker.skill_cooldowns[skill.SkillID] = skill.CD
                        reward += damage
                        total_attack_timer += attack_timer
                else:
                    self.gui.root.after(
                        100, lambda: self.attack_loop(attacker, target)
                    )
                    return
                    
        self.gui.display_battle_log(self.get_battle_log())  
        self.update_hp_mp()
        next_state = ai.get_state(attacker, target)       
        ai.update_q(state, result, reward, next_state)        
        attacker.attackTimerFunc = self.gui.root.after(int(total_attack_timer*1000) ,lambda: self.attack_loop(attacker, target))
        
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