from game_models import SkillData,SkillOperationData
from commonfunction import CommonFunction
from typing import Tuple

class SkillProcessor:
    # from battle_simulator import BattleSimulator,BattleCharacter
    @staticmethod
    def _execute_operation(skillData: SkillData, attacker, defender)-> Tuple[str, int, float]:
        """
        實現技能效果執行入口
        """
        if(skillData.Name != "普通攻擊"):
            for op in skillData.SkillOperationDataList:
                #取得施放對象
                target = attacker if op.EffectRecive == 0 else defender

                match op.SkillComponentID:
                    case "Damage":
                        return attacker.HitCalculator(skillData,defender)
                    case "CrowdControl":
                        target.CrowdControlCalculator(op)
                        return f"{attacker.name} 使 {target.name} 進入 {op.duration} 秒的控制狀態",0,0
                    case "Lunge":
                        pass
                    case "MultipleDamage":
                        pass
                    case "ContinuanceBuff":
                        target.add_buff_effect(skillData)
                        temp = f"{CommonFunction.get_text('TM_'+op.InfluenceStatus)}: {CommonFunction.get_text('TM_' + op.AddType).format(op.EffectValue)}"
                        return f"{attacker.name} 對 {target.name} 使用 Buff：{temp}，持續 {op.EffectDurationTime} 秒",0,0.5
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
                        return f"{attacker.name} 對 {target.name} 使用 Debuff：{op.attr} -{op.value}，持續 {op.duration} 回合",0,0
                    case "PassiveBuff":
                        target.SkillEffectStatusOperation(op.InfluenceStatus,(op.AddType == "Rate"),op.EffectValue)
                        temp = f"{CommonFunction.get_text('TM_'+op.InfluenceStatus)}: {CommonFunction.get_text('TM_' + op.AddType).format(op.EffectValue)}"
                        return f"{attacker.name} 對 {target.name} 啟動 被動技能：{temp}",0,0
        else:
            return attacker.HitCalculator(skillData,defender)



