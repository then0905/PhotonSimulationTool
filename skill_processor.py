from game_models import ItemDataModel, SkillData, SkillOperationData, ItemEffectData,GameData
from commonfunction import CommonFunction
from typing import Tuple, Optional
import copy

class SkillProcessor:
    @staticmethod
    def _execute_skill_operation(skillData: SkillData, attacker, defender)-> Optional[Tuple[str, int, float]]:
        """實現技能效果執行入口"""
        returnResult = []

        # 普通攻擊特殊處理
        if skillData.Name == "普通攻擊":
            #模擬技能端的資料儲存方式 參考Damage組件
            attackerResult = attacker.HitCalculator(skillData, defender)
            for result in attackerResult:
                returnResult.append(result)

            return returnResult

        # 執行效果
        skillResult = SkillProcessor._execute_component(skillData, attacker, defender)
        returnResult.append(skillResult)

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
    def _execute_component(skillData: SkillData,
                           attacker, defender) -> Optional[Tuple[str, int, float]]:
        """執行單個技能組件"""
        returnResult = []
        execution_history = {}  # 記錄每個效果的執行結果

        for index, op in enumerate(skillData.SkillOperationDataList):
            # 依賴判斷（核心邏輯）
            if not SkillProcessor._check_dependency(op, execution_history):
                execution_history[index] = {
                    "componentID": op.SkillComponentID, "success": False}
                continue

            # 取得施放對象
            target = attacker if op.EffectRecive in [0, -2, -3] else defender

            # 先找出是否有升級技能資料
            upgradeDataList = attacker.upgrade_skill_dict.get(skillData.SkillID)

            if (upgradeDataList is not None):
                lastUpgradeData = upgradeDataList[-1]
                tempSkillData = SkillProcessor.upgrade_skill_processor(lastUpgradeData, skillData)
            else:
                tempSkillData = skillData

            # 先找出是否有強化技能資料
            enhanceDataList = attacker.enhance_skill_dict.get(skillData.SkillID)

            if (enhanceDataList is not None):
                tempSkillData = SkillProcessor.enhance_skill_processor(enhanceDataList, tempSkillData)

            # 記錄執行結果
            success = True

            match op.SkillComponentID:
                case "Damage":
                    attackerResult = attacker.HitCalculator(tempSkillData, target)
                    for result in attackerResult:
                        returnResult.append(result)
                    # 判斷是否成功：damage > 0 或有效果觸發
                    temp = attackerResult[0]
                    success = temp[1] > 0
                case "ElementDamage":
                    temp = attacker.ElementAttackCalulator(tempSkillData,op, target)
                    returnResult.append(temp)
                    # 判斷是否成功：damage > 0 或有效果觸發
                    success = temp[1] > 0 if len(temp) > 1 else True

                case "CrowdControl":
                    returnResult.append(SkillProcessor.status_skill_effect_start(op, attacker, target))

                case "MultipleDamage":
                    attackerResult = attacker.HitCalculator(tempSkillData, target)
                    for result in attackerResult:
                        returnResult.append(result)
                    temp = attackerResult[0]
                    # 判斷是否成功：damage > 0 或有效果觸發
                    success = temp[1] > 0 if len(temp) > 1 else True

                case "ContinuanceBuff":
                    target.add_skill_buff_effect(tempSkillData, op)
                    temp = f"{CommonFunction.get_text('TM_' + op.InfluenceStatus)}: {CommonFunction.get_text('TM_' + op.AddType).format(op.EffectValue)}"
                    returnResult.append((CommonFunction.battlelog_text_processor({
                        "caster_text": attacker.name,
                        "descript_text": temp,
                        "target_text": target.name,
                    }, "continuanceBuff", op.EffectDurationTime), 0, 0.5))

                case "AdditiveBuff":
                    target.additive_buff_event += lambda: SkillProcessor.skill_additive_effect_event(
                        tempSkillData, op, target)
                    temp = f"{CommonFunction.get_text('TM_' + op.InfluenceStatus)}: {CommonFunction.get_text('TM_' + op.AddType).format(op.EffectValue)}"
                    returnResult.append((CommonFunction.battlelog_text_processor({
                        "caster_text": attacker.name,
                        "descript_text": temp,
                        "target_text": target.name,
                    }, "additiveBuff", op.EffectDurationTime), 0, 0.5))

                case "Debuff":
                    returnResult.append(SkillProcessor.status_skill_effect_start(op, attacker, target))

                case "PassiveBuff":
                    target.add_skill_passive_effect(tempSkillData, op)
                    # target.SkillEffectStatusOperation(
                    # op.InfluenceStatus, (op.AddType == "Rate"), op.EffectValue)
                    temp = f"{CommonFunction.get_text('TM_' + op.InfluenceStatus)}: {CommonFunction.get_text('TM_' + op.AddType).format(op.EffectValue)}"
                    returnResult.append((CommonFunction.battlelog_text_processor({
                        "caster_text": attacker.name,
                        "descript_text": temp,
                        "target_text": target.name,
                    }, "passiveBuff",CommonFunction.get_text(f"TM_{tempSkillData.SkillID}_Name")), 0, 0))

                case "Utility":
                    returnResult.append(SkillProcessor.skill_utility_processor(target, op))

                case "Health":
                    returnResult.append(target.processRecovery(op,skillData.Name, attacker, target))

                case "EnhanceSkill":
                    # 強化指定技能 在角色開一個新字典<BonusId,下個component資料>
                    attacker.passive_bar.add_skill_effect(tempSkillData.SkillID, tempSkillData)
                    key = op.Bonus[0]

                    if key not in attacker.enhance_skill_dict:
                        attacker.enhance_skill_dict[key] = []

                    attacker.enhance_skill_dict[key].append(tempSkillData)
                    returnResult.append((CommonFunction.battlelog_text_processor({
                        "caster_text": attacker.name,
                        "target_text": CommonFunction.get_text(tempSkillData.Name),
                        "descript_text": CommonFunction.get_text(GameData.Instance.SkillDataDic[key].Name),
                    }, "enhanceSkill"), 0, 0))
                    break
                case "UpgradeSkill":
                    # 升級指定技能 在角色開一個新字典<BonusId,下個component資料>
                    attacker.passive_bar.add_skill_effect(tempSkillData.SkillID, tempSkillData)
                    key = op.Bonus[0]

                    if key not in attacker.upgrade_skill_dict:
                        attacker.upgrade_skill_dict[key] = []

                    attacker.upgrade_skill_dict[key].append(tempSkillData)
                    returnResult.append((CommonFunction.battlelog_text_processor({
                        "caster_text": attacker.name,
                        "target_text": CommonFunction.get_text(tempSkillData.Name) ,
                        "descript_text": CommonFunction.get_text(GameData.Instance.SkillDataDic[key].Name),
                    }, "upgradeSkill"), 0, 0))
                case _:
                    returnResult.append(("",0,0))

            execution_history[index] = {
                "componentID": op.SkillComponentID,
                "success": success
            }
        return returnResult

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
                        defender.processRecovery(op,itemData.Name, attacker, defender))
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
                defender.SkillEffectStatusOperation(op.InfluenceStatus, (op.AddType == "Rate"), op.EffectValue)
                defender.add_debuff_effect(op)
                return (CommonFunction.battlelog_text_processor({
                    "caster_text": attacker.name,
                    "descript_text": CommonFunction.get_text("TM_" + op.InfluenceStatus + "_Name"),
                    "target_text": defender.name,
                }, "debuffStart", op.EffectDurationTime), 0, 0)

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
        技能條件檢查(Operation版)
        """
        if (not any(op.ConditionOR) and not any(op.ConditionAND)):
            return True
        or_list = []
        if (any(op.ConditionOR)):
            for or_data in op.ConditionOR:
                temp_or_data = or_data.split('_')
                temp_or_data_second = '_'.join(temp_or_data[1:])
                or_list.append(SkillProcessor.skill_condition_check(
                    caster, temp_or_data[0], temp_or_data_second))
        else:
            or_list.append(True)
        and_list = []
        if (any(op.ConditionAND)):
            for and_data in op.ConditionAND:
                temp_and_data = and_data.split('_')
                temp_and_data_second = '_'.join(temp_and_data[1:])
                and_list.append(SkillProcessor.skill_condition_check(
                    caster, temp_and_data[0], temp_and_data_second))
        else:
            and_list.append(True)

        return any(or_list) and all(and_list)

    @staticmethod
    def skill_all_condition_process(caster, skillData: SkillData) -> bool:
        """
        技能條件檢查(Skill版)
        """
        result = []
        for op in skillData.SkillOperationDataList:
            result.append(SkillProcessor.skill_condition_process(caster, op))
        return all(result)

    @staticmethod
    def skill_condition_check(caster, key: str, value) -> bool:
        """
        技能效果條件檢查
        """
        match(key):
            case "EquipWeapon":
                if (caster.equipped_weapon is None):
                    return False
                return any(x[0].TypeID == str(value)
                           for x in caster.equipped_weapon)
            case "EquipLeft":
                if (caster.equipped_weapon is None):
                    return False
                return any(x[0].TypeID == str(value)
                           for x in caster.equipped_weapon)
            # 全副武裝
            case "EquipArmor":
                if (caster.equipped_armor is None):
                    return False
                return (len(caster.equipped_armor) == 5 and
                        all(x[0].TypeID == str(value)
                        for x in caster.equipped_armor))
            case "InCombatStatus":
                # 模擬總是在戰鬥中 所以一律回傳true
                return True
            case "HpLess":
                return caster.stats["HP"] < (float(value)*caster.stats["MaxHP"])
            #尋找作用中的疊層效果
            case "Stack":
                return 0 < caster.passive_bar.get_effect_stack(value)

    @staticmethod
    def skill_additive_effect_event(skillData: SkillData, op, target):
        """
        疊加型技能效果 事件呼叫
        """
        if (SkillProcessor.skill_condition_process(target, op)):
            target.add_skill_addtive_effect(skillData, op, 1)

    @staticmethod
    def skill_utility_processor(caster,op):
        """
        功能型技能 處理
        """
        match op.InfluenceStatus:
            #清除指定技能所有疊層
            case "RemoveAdditive":
                get_stack = caster.passive_bar.get_effect_stack(str(op.Bonus[0]))
                target_skill = GameData.Instance.SkillDataDic[str(op.Bonus[0])]
                #暫存消耗的層數
                caster.temp_dict[str(op.Bonus[0])] = get_stack
                #重製目標技能疊層
                caster.set_skill_addtive_effect(target_skill,op,0)
                return (CommonFunction.battlelog_text_processor({
                    "caster_text": caster.name,
                    "descript_text": CommonFunction.get_text(target_skill.Name),
                }, "removeAdditive",get_stack), 0, 0)

            #清除控制技能
            case "RemoveAllCC":
                debuffskills = list(caster.debuff_skill.keys())
                for skillid in debuffskills:
                    caster.debuff_bar(skillid)
                caster.debuff_skill = {}
                return (CommonFunction.battlelog_text_processor({
                    "caster_text": caster.name,
                    "descript_text": CommonFunction.get_text(f"TM_{op.SkillID}_Name"),
                }, "removeAllCC"), 0, 0)

    @staticmethod
    def skill_continuancebuff_bonus_processor(caster,op):
        """持續型buff技能的Bonus資料處理"""
        temp_bonus_data = op.Bonus
        match temp_bonus_data[0]:
            case "Stack":
                key = temp_bonus_data[1]
                stack = caster.temp_dict.get(key, 0)
                caster.temp_dict.pop(temp_bonus_data[1], None)
                return int(stack)

    @staticmethod
    def upgrade_skill_processor(upgradeSkillData, skillData: SkillData)-> SkillData:
        """
        升級技能處理
        """

        #暫存 技能資料 並修改
        tempSkillData = copy.deepcopy(skillData)
        tempSkillData.Damage = upgradeSkillData.Damage
        tempSkillData.CastMage = upgradeSkillData.CastMage
        tempSkillData.CD = upgradeSkillData.CD
        tempSkillData.Distance = upgradeSkillData.Distance
        tempSkillData.Width = upgradeSkillData.Width
        tempSkillData.Height = upgradeSkillData.Height
        tempSkillData.CircleDistance = upgradeSkillData.CircleDistance
        tempSkillData.Name = upgradeSkillData.Name
        tempSkillData.Intro = upgradeSkillData.Intro

        for tempOp in upgradeSkillData.SkillOperationDataList:
            if(tempOp.SkillComponentID == "UpgradeSkill"):
                upgradeSkillId = tempOp.Bonus[0]
                upgradeComponentId = tempOp.Bonus[1]
                upgradeComponentIndex = tempOp.Bonus[2]
                sameComponentIds = [s for s in tempSkillData.SkillOperationDataList if s.SkillComponentID == upgradeComponentId]
                targetSkillOpData = sameComponentIds[int(upgradeComponentIndex)]
                #替換Op資料
                targetSkillOpData.DependCondition = tempOp.DependCondition
                targetSkillOpData.EffectValue = tempOp.EffectValue
                targetSkillOpData.InfluenceStatus = tempOp.InfluenceStatus
                targetSkillOpData.AddType = tempOp.AddType
                targetSkillOpData.ConditionOR = tempOp.ConditionOR
                targetSkillOpData.ConditionAND = tempOp.ConditionAND
                targetSkillOpData.EffectDurationTime = tempOp.EffectDurationTime
                targetSkillOpData.EffectRecive = tempOp.EffectRecive
                targetSkillOpData.TargetCount = tempOp.TargetCount

        return tempSkillData

    @staticmethod
    def enhance_skill_processor(enhanceSkillDataList , skillData: SkillData):
        """
        強化技能處理
        """

        # 暫存 技能資料 並修改
        tempSkillData = copy.deepcopy(skillData)

        # 展開所有 enhanceSkillDataList 裡的 operation
        enhance_ops = [
            op
            for skill in enhanceSkillDataList
            for op in skill.SkillOperationDataList
            if op.SkillComponentID == "EnhanceSkill"
        ]

        tempSkillData.SkillOperationDataList = [
            *skillData.SkillOperationDataList,
            *enhance_ops
        ]

        return tempSkillData

