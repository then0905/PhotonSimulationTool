"""
輕量級的記憶體內 GUI 替代物件，
用於快速略過戰鬥時取代真正的 tkinter 元件。
"""

from commonfunction import clamp
from game_models import GameData


class DummyStatusEffectBar:
    """
    模擬 StatusEffectBar 的資料介面，
    不做任何視覺渲染，僅在記憶體中追蹤效果與疊層。
    """

    def __init__(self):
        self.effects = []  # list of {"id": str, "stack": int, "skill": object}

    def add_skill_effect(self, id: str, skill, stack_count=0):
        """增加技能效果（含疊層邏輯）"""
        if stack_count > 0:
            for eff in self.effects:
                if eff["id"] == id:
                    # 疊層上限來自 skill.SkillOperationDataList[0].Bonus[0]
                    max_stack = int(skill.SkillOperationDataList[0].Bonus[0])
                    eff["stack"] = clamp(eff["stack"] + stack_count, 0, max_stack)
                    return
        self.effects.append({"id": id, "stack": stack_count, "skill": skill})

    def add_item_effect(self, id: str, item, stack_count=0):
        """增加道具效果"""
        self.effects.append({"id": id, "stack": stack_count, "item": item})

    def add_debuff(self, id: str, effectId, stack_count=0):
        """增加負面狀態效果"""
        self.effects.append({"id": id, "stack": stack_count, "effectId": effectId})

    def remove_effect(self, id):
        """移除指定 id 的效果"""
        self.effects = [eff for eff in self.effects if eff["id"] != id]

    def get_effect_stack(self, id) -> int:
        """取得指定效果的疊層數"""
        for eff in self.effects:
            if eff["id"] == id or eff["id"].startswith(id):
                return eff["stack"]
        return 0

    def set_effect_stack(self, id, target_stack):
        """設定指定效果的疊層數"""
        for eff in self.effects:
            if eff["id"] == id or eff["id"].startswith(id):
                eff["stack"] = target_stack

    def clear_bar(self):
        """清空所有效果"""
        self.effects = []


class DummyCharacterOverview:
    """
    模擬 CharacterOverviewWnd 的資料介面，
    僅儲存最新的 stats，不渲染任何視窗。
    """

    def __init__(self):
        self.status = {}

    def update_state(self, status: dict):
        self.status = status


class DummyItemManager:
    """
    模擬 ItemManager 的資料介面，
    追蹤道具消耗但不更新任何 UI。
    """

    def __init__(self, carried_items: dict = None):
        # carried_items 格式: {item_id: {"count": int, "data": ItemDataModel}}
        self.carried_items = carried_items if carried_items is not None else {}
        self.item_labels = {}

    def consume_item(self, item_id, amount=1):
        """消耗道具"""
        if item_id not in self.carried_items:
            return False
        if self.carried_items[item_id]["count"] < amount:
            return False
        self.carried_items[item_id]["count"] -= amount
        return True
