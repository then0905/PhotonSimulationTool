from platform import android_ver

from fontTools.ufoLib import fontInfoOpenTypeNameRecordsValidator
from fontTools.varLib.models import nonNone

from game_models import ItemDataModel, SkillData, SkillOperationData, ItemEffectData
from commonfunction import CommonFunction
from typing import Tuple, Optional


class SkillProcessor:
    @staticmethod
    def _execute_skill_operation(skillData: SkillData, attacker, defender, gui=None) -> Tuple[str, int, float]:
        """實現技能效果執行入口"""
        returnResult = []
        execution_history = {}  # 記錄每個效果的執行結果

        # 普通攻擊特殊處理
        if skillData.Name == "普通攻擊":
            returnResult.append(attacker.HitCalculator(skillData, defender))
            return returnResult

        # 遍歷所有技能效果
        for index, op in enumerate(skillData.SkillOperationDataList):
            # 條件檢查
            if not SkillProcessor.skill_condition_process(attacker, op):
                execution_history[index] = {
                    "componentID": op.SkillComponentID, "success": False}
                continue

            # 依賴判斷（核心邏輯）
            if not SkillProcessor._check_dependency(op, execution_history):
                execution_history[index] = {
                    "componentID": op.SkillComponentID, "success": False}
                continue

            # 取得施放對象
            target = attacker if op.EffectRecive in [0, -2, -3] else defender

            # 執行效果
            result = SkillProcessor._execute_component(
                op, skillData, attacker, target, defender)

            # 記錄執行結果
            success = False
            if result:
                returnResult.append(result)
                # 判斷是否成功：damage > 0 或有效果觸發
                success = result[1] > 0 if len(result) > 1 else True

            execution_history[index] = {
                "componentID": op.SkillComponentID,
                "success": success
            }

        return returnResult

    @staticmethod
    def _check_dependency(op: SkillOperationData, history: dict) -> bool:
        """
        檢查依賴條件是否滿足

        Args:
            op: 當前技能操作
            history: 執行歷史 {index: {"componentID": str, "success": bool}}

        Returns:
            是否可以執行
        """
        depend = op.DependCondition

        # 規則 1: 空字串 = 無依賴
        if not depend or depend == "" or depend == "None":
            return True

        # 規則 2: "All" = 依賴所有前面的效果成功
        if depend == "All":
            return all(item["success"] for item in history.values())

        # 規則 3: "Prev" = 依賴上一個效果
        if depend == "Prev":
            if not history:
                return True  # 第一個效果
            last_index = max(history.keys())
            return history[last_index]["success"]

        # 規則 4: "!ComponentID" = 反向依賴（失敗才執行）
        if depend.startswith("!"):
            target_component = depend[1:]
            for item in history.values():
                if item["componentID"] == target_component:
                    return not item["success"]  # 失敗才執行
            return True  # 找不到目標組件，預設可執行

        # 規則 5: "ComponentID" 或 "Comp1,Comp2" = 依賴特定組件成功
        target_components = [c.strip() for c in depend.split(",")]
        for item in history.values():
            if item["componentID"] in target_components and item["success"]:
                return True  # 任一匹配成功即可

        return False  # 找不到成功的依賴

    @staticmethod
    def _execute_component(op: SkillOperationData, skillData: SkillData,
                           attacker, target, defender) -> Optional[Tuple[str, int, float]]:
        """執行單個技能組件"""
        match op.SkillComponentID:
            case "Damage":
                return attacker.HitCalculator(skillData, defender)

            case "CrowdControl":
                return SkillProcessor.status_skill_effect_start(op, attacker, target)

            case "MultipleDamage":
                return attacker.HitCalculator(skillData, defender)

            case "ContinuanceBuff":
                target.add_skill_buff_effect(skillData, op)
                temp = f"{CommonFunction.get_text('TM_' + op.InfluenceStatus)}: {CommonFunction.get_text('TM_' + op.AddType).format(op.EffectValue)}"
                return (CommonFunction.battlelog_text_processor({
                    "caster_text": attacker.name,
                    "descript_text": temp,
                    "target_text": target.name,
                }, "continuanceBuff", op.EffectDurationTime), 0, 0.5)

            case "AdditiveBuff":
                target.additive_buff_event += lambda: SkillProcessor.skill_additive_effect_event(
                    skillData, op, target)
                temp = f"{CommonFunction.get_text('TM_' + op.InfluenceStatus)}: {CommonFunction.get_text('TM_' + op.AddType).format(op.EffectValue)}"
                return (CommonFunction.battlelog_text_processor({
                    "caster_text": attacker.name,
                    "descript_text": temp,
                    "target_text": target.name,
                }, "additiveBuff", op.EffectDurationTime), 0, 0.5)

            case "Debuff":
                return SkillProcessor.status_skill_effect_start(op, attacker, target)

            case "PassiveBuff":
                target.add_skill_passive_effect(skillData,op)
                #target.SkillEffectStatusOperation(
                    #op.InfluenceStatus, (op.AddType == "Rate"), op.EffectValue)
                temp = f"{CommonFunction.get_text('TM_' + op.InfluenceStatus)}: {CommonFunction.get_text('TM_' + op.AddType).format(op.EffectValue)}"
                return (CommonFunction.battlelog_text_processor({
                    "caster_text": attacker.name,
                    "descript_text": temp,
                    "target_text": target.name,
                }, "passiveBuff"), 0, 0)

            case _:
                return None

    @staticmethod
    def execute_item_operation(itemData: ItemDataModel, attacker, defender, gui=None) -> Tuple[str, int, float]:
        """
        實現道具效果執行入口
        """
        # 儲存回傳的結果
        returnResult = []
        for op in itemData.ItemEffectDataList:
            match op.ItemComponentID:
                case "Restoration":
                    returnResult.append(
                        defender.processRecovery(op, attacker, defender))
                case "Utility":
                    pass
                case "Continuance":
                    attacker.add_item_buff_effect(op, itemData)
                    temp = f"{CommonFunction.get_text('TM_'+op.InfluenceStatus)}: {CommonFunction.get_text('TM_' + op.AddType).format(op.EffectValue)}"
                    returnResult.append(CommonFunction.battlelog_text_processor({
                        "caster_text": attacker.name,
                        "descript_text": temp,
                        "target_text": defender.name,
                    }, "continuanceBuff", op.EffectDurationTime), 5, 0.5)
        return returnResult

    @staticmethod
    def status_skill_effect_start(op: SkillOperationData, attacker, defender) -> Tuple[str, int, float]:
        """
        狀態效果啟動方法
        """
        match op.SkillComponentID:
            case "CrowdControl":
                defender.CrowdControlCalculator(op, 1)
                defender.add_debuff_effect(op)
                return (CommonFunction.battlelog_text_processor({
                    "caster_text": attacker.name,
                    "descript_text": CommonFunction.get_text("TM_" + op.InfluenceStatus + "_Name"),
                    "target_text": defender.name,
                }, "crowdControlStart", op.EffectDurationTime), 0, 0)
            case "Debuff":
                defender.add_debuff_effect(op)
                return (CommonFunction.battlelog_text_processor({
                    "caster_text": attacker.name,
                    "descript_text": CommonFunction.get_text("TM_" + op.InfluenceStatus + "_Name"),
                    "target_text": defender.name,
                }, "debuffControlStart", op.EffectDurationTime), 0, 0)

    @staticmethod
    def status_skill_effect_end(op: SkillOperationData, character) -> Tuple[str, int, float]:
        """
        狀態效果結束方法
        """
        match op.SkillComponentID:
            case "CrowdControl":
                character.CrowdControlCalculator(op, -1)
                return (CommonFunction.battlelog_text_processor({
                    "caster_text": character.name,
                    "descript_text": CommonFunction.get_text("TM_" + op.InfluenceStatus + "_Name"),
                }, "crowdControlEnd", op.EffectDurationTime), 0, 0)
            case "Debuff":
                # defender.apply_debuff(op.attr, op.value, op.duration)
                return (CommonFunction.battlelog_text_processor({
                    "caster_text": character.name,
                    "descript_text": CommonFunction.get_text("TM_" + op.InfluenceStatus + "_Name"),
                }, "debuffEnd", op.EffectDurationTime), 0, 0)

    @staticmethod
    def skill_condition_process(caster, op: SkillOperationData) -> bool:
        """
        技能施放條件檢查入口
        """
        if (any(op.ConditionOR) and any(op.ConditionAND)):
            return True
        or_list = []
        if (any(op.ConditionOR)):
            for or_data in op.ConditionOR:
                temp_or_data = or_data.split('_')
                or_list.append(SkillProcessor.skill_condition_check(
                    caster, temp_or_data[0], temp_or_data[1]))
        else:
            or_list.append(True)
        and_list = []
        if (any(op.ConditionAND)):
            for and_data in op.ConditionAND:
                temp_and_data = and_data.split('_')
                and_list.append(SkillProcessor.skill_condition_check(
                    caster, temp_and_data[0], temp_and_data[1]))
        else:
            and_list.append(True)

        return any(or_list) and all(and_list)

    @staticmethod
    def skill_condition_check(caster, key: str, value) -> bool:
        """
        技能效果條件檢查
        """
        match(key):
            case "EquipWeapon":
                if (caster.equipped_weapon is None):
                    return False
                return any(x.CodeID == str(value)
                           for x in caster.equipped_weapon)
            case "EquipLeft":
                if (caster.equipped_weapon is None):
                    return False
                return any(x.TypeID == str(value)
                           for x in caster.equipped_weapon)
            # 全副武裝
            case "EquipArmor":
                if (caster.equipped_armor is None):
                    return False
                return (len(caster.equipped_armor) == 5 and
                        all(x.TypeID == str(caster.equipped_armor.value)
                        for x in caster.equipped_armor))
            case "InCombatStatus":
                # 模擬總是在戰鬥中 所以一律回傳true
                return True
            case "HpLess":
                return caster.stats["HP"] < (value*caster.stats["MaxHP"])

    @staticmethod
    def skill_additive_effect_event(skillData: SkillData, op, target):
        """
        疊加型技能效果 事件呼叫
        """
        if (SkillProcessor.skill_condition_process(target, op)):
            target.add_skill_addtive_effect(skillData, op, 1)
