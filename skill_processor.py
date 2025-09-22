from game_models import ItemDataModel, SkillData,SkillOperationData,ItemEffectData
from commonfunction import CommonFunction
from typing import Tuple

class SkillProcessor:
    # from battle_simulator import BattleSimulator,BattleCharacter
    @staticmethod
    def _execute_skill_operation(skillData: SkillData, attacker, defender, gui =None)-> Tuple[str, int, float]:
        """
        實現技能效果執行入口
        """
        #儲存回傳的結果
        returnResult = []
        if(skillData.Name != "普通攻擊"):
            for op in skillData.SkillOperationDataList:
                #取得施放對象
                target = attacker if op.EffectRecive in [0,-2,-3] else defender

                match op.SkillComponentID:
                    case "Damage":
                        returnResult.append(attacker.HitCalculator(skillData,defender))
                    case "CrowdControl":
                        returnResult.append(SkillProcessor.status_skill_effect_start(op,attacker,target))
                    case "Lunge":
                        pass
                    case "MultipleDamage":
                        returnResult.append( attacker.HitCalculator(skillData,defender))
                    case "ContinuanceBuff":
                        target.add_skill_buff_effect(skillData,op)
                        temp = f"{CommonFunction.get_text('TM_'+op.InfluenceStatus)}: {CommonFunction.get_text('TM_' + op.AddType).format(op.EffectValue)}"
                        returnResult.append((f"{attacker.name} 對 {target.name} 使用 Buff：{temp}，持續 {op.EffectDurationTime} 秒",0,0.5))
                    case "AdditiveBuff":
                        pass
                    case "Channeled":
                        pass
                    case "Utility":
                        pass
                    case "ElementDamage":
                        pass
                    case "Debuff":
                        target.apply_debuff(op.attr, op.value, op.duration)
                        return ((f"{attacker.name} 對 {target.name} 使用 Debuff：{op.attr} -{op.value}，持續 {op.duration} 回合",0,0))
                    case "PassiveBuff":
                        target.SkillEffectStatusOperation(op.InfluenceStatus,(op.AddType == "Rate"),op.EffectValue)
                        temp = f"{CommonFunction.get_text('TM_'+op.InfluenceStatus)}: {CommonFunction.get_text('TM_' + op.AddType).format(op.EffectValue)}"
                        returnResult.append((f"{attacker.name} 對 {target.name} 啟動 被動技能：{temp}",0,0))
        else:
            returnResult.append(attacker.HitCalculator(skillData,defender))
        return returnResult

    @staticmethod
    def execute_item_operation(itemData:ItemDataModel,attacker,defender,gui = None) -> Tuple[str,int,float]:
        """
        實現道具效果執行入口
        """
        #儲存回傳的結果
        returnResult = []
        for op in itemData.ItemEffectDataList:
            match op.ItemComponentID:
                case "Restoration":
                    returnResult.append(defender.processRecovery(op,attacker,defender))
                case "Utility":
                    pass
                case "Continuance":
                    attacker.add_item_buff_effect(op,itemData)
                    temp = f"{CommonFunction.get_text('TM_'+op.InfluenceStatus)}: {CommonFunction.get_text('TM_' + op.AddType).format(op.EffectValue)}"
                    returnResult.append((f"{attacker.name} 對 {defender.name} 使用道具：{temp}，持續 {op.EffectDurationTime} 秒",5,0.5))
        return returnResult

    @staticmethod
    def status_skill_effect_start(op: SkillOperationData, attacker, defender)-> Tuple[str, int, float]:
        """
        狀態效果啟動方法
        """
        match op.SkillComponentID:
            case "CrowdControl":
                defender.CrowdControlCalculator(op,1)
                defender.add_debuff_effect(op)
                return f"{attacker.name} 使 {defender.name} 進入 {op.EffectDurationTime} 秒的{CommonFunction.get_text("TM_"+ op.InfluenceStatus+"_Name")}控制狀態",0,0
            case "Debuff":
                defender.apply_debuff(op.attr, op.value, op.duration)
                return f"{attacker.name} 對 {defender.name} 使用 Debuff：{op.attr} -{op.value}，持續 {op.duration} 回合",0,0
            
    @staticmethod                    
    def status_skill_effect_end(op: SkillOperationData, character)-> Tuple[str, int, float]:
        """
        狀態效果結束方法
        """
        match op.SkillComponentID:
            case "CrowdControl":
                character.CrowdControlCalculator(op,-1)
                return f"{character.name} 解除了 {CommonFunction.get_text("TM_"+ op.InfluenceStatus+"_Name")}的控制狀態",0,0
            case "Debuff":
                # defender.apply_debuff(op.attr, op.value, op.duration)
                return f"{character.name} 對 {character.name} 使用 Debuff：{op.attr} -{op.value}，持續 {op.duration} 回合",0,0


