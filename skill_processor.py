from game_models import SkillData,SkillOperationData

class SkillProcessor:
    from battle_simulator import BattleSimulator,BattleCharacter
    def _execute_operation(self, op: SkillOperationData, attacker: BattleCharacter, defender: BattleCharacter,battleSimulator:BattleSimulator, turn):
        """
        實現技能效果執行入口
        """
        target = attacker if op.target == "Self" else defender

        match op.SkillComponentID:
            case "Damage":
                damage = attacker.HitCalculator(None, target, op.formula or op.value)
                battleSimulator.battle_log.append(f"{attacker.name} 對 {target.name} 造成 {damage} 傷害！")
            case "CrowdControl":
                target.CrowdControlCalculator(op)
                battleSimulator.battle_log.append(f"{attacker.name} 使 {target.name} 進入 {op.duration} 秒的控制狀態")
            case "Lunge":
                pass
            case "MultipleDamage":
                pass
            case "ContinuanceBuff":
                target.apply_buff(op.attr, op.value, op.duration)
                battleSimulator.battle_log.append(f"{attacker.name} 對 {target.name} 使用 Buff：{op.attr} +{op.value}，持續 {op.duration} 回合")
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
                battleSimulator.battle_log.append(f"{attacker.name} 對 {target.name} 使用 Debuff：{op.attr} -{op.value}，持續 {op.duration} 回合")




