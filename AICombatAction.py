import os
import pickle
import random
from collections import defaultdict
from game_models import GameData

class ai_action:
    SAVE_DIR = "q_tables"  # 存放所有Q表的資料夾

    def __init__(self, role_id: str,skills,item):
        """
                role_id: 職業/怪物的唯一識別碼 (例如 "Warrior", "Mage", "Slime001")
                skills: 該角色的技能清單
                items: 該角色的道具清單
        """
        self.role_id = role_id
        self.skills = skills
        self.item = item
        self.Q = defaultdict(float)  # Q表
        self.alpha = 0.1  # 學習率
        self.gamma = 0.9  # 折扣因子
        self.epsilon = 0.2  # 探索率

        # 確保目錄存在
        os.makedirs(self.SAVE_DIR, exist_ok=True)
        # 嘗試讀取舊的Q表
        self.Q = self.load_q_table()

    # -----------------------------
    # 儲存與讀取
    # -----------------------------

    def _save_path(self):
        """回傳這個角色的Q表檔案路徑"""
        return os.path.join(self.SAVE_DIR, f"q_table_{self.role_id}.pkl")

    def load_q_table(self):
        """讀取Q表"""
        path = self._save_path()
        if os.path.exists(path):
            with open(path, "rb") as f:
                q_table = pickle.load(f)

            # 顯示讀取的Q表資訊
            # print("✅ 成功載入 Q 表")
            # print("目前 Q 表紀錄數量：", len(q_table))
            # if len(q_table) > 0:
            #     print("範例 Q 值：", list(q_table.items())[:5])
            # else:
            #     print("Q 表是空的")

            return q_table
        # else:
        #     print("⚠️ 找不到 Q 表檔案，將建立新的")
        return defaultdict(float)

    def save_q_table(self):
        """儲存Q表"""
        path = self._save_path()
        with open(path, "wb") as f:
            pickle.dump(self.Q, f)
        # print("✅ 已儲存 Q 表")
        # print("目前 Q 表紀錄數量：", len(self.Q))
        # print("範例 Q 值：", list(self.Q.items())[:5])

    def get_state(self, attacker, target):
        # 生成戰鬥狀態向量
        current_active_buff = [s for s in attacker.buff_skill or {}]
        current_cooldown_buff = [s for s in attacker.skill_cooldowns or {}]
        
        mp_ratio = attacker.stats["MP"] / attacker.stats["MaxMP"] if attacker.stats["MaxMP"] > 0 else 0
        hp_ratio = attacker.stats["HP"] / attacker.stats["MaxHP"] if attacker.stats["MaxHP"] > 0 else 0
        target_hp_ratio = target.stats["HP"] / target.stats["MaxHP"] if target.stats["MaxHP"] > 0 else 0

        state = (
            round(hp_ratio, 2),
            round(mp_ratio, 2),
            round(target_hp_ratio, 2),
            int(attacker.controlled_for_attack > 0),
            int(attacker.controlled_for_skill > 0),
        )
        
        filtered_skills =  [s for s in self.skills if s.Characteristic is True]

        #buff效果
        buff_features = []
        for s in filtered_skills:
            if s.SkillID in attacker.buff_skill:
                # 從字典中拿剩餘時間
                remaining_time = attacker.buff_skill[s.SkillID][1]
                # 最大時間
                max_time = attacker.buff_skill[s.SkillID][0].SkillOperationDataList[0].EffectDurationTime
            else:
                remaining_time = 0.0
                max_time = 1.0  # 避免除零
                
            buff_features.append(remaining_time / max_time)
            
         # 技能冷卻狀態
        cooldown_features = []
        for s in filtered_skills:
            if s.SkillID in attacker.skill_cooldowns:
                # 從字典中拿剩餘時間
                remaining_time = attacker.skill_cooldowns[s.SkillID]
                # 最大時間
                max_time = GameData.Instance.SkillDataDic[s.SkillID].CD
            else:
                remaining_time = 0.0
                max_cd = 1.0
            if max_time <= 0:
                cooldown_features.append(0.0)
            else:
                cooldown_features.append(remaining_time / max_time)

        # 可以加更多資訊，如buff狀態
        return tuple(list(state)+buff_features+cooldown_features)

    def choose_action(self, self_char, enemy):
        state = self.get_state(self_char, enemy)

        # === 合法動作清單 ===
        actions = ["NORMAL_ATTACK"]
        for s in self.skills:
            characteristic = s.Characteristic
            mp_ok = (self_char.stats["MP"] - s.CastMage) > 0
            cd_ok = s.SkillID not in self_char.skill_cooldowns  # 沒在CD才能放
            skill_not_running =  s.SkillID not in self_char.buff_skill  # 若是buff且沒再運作中
            if mp_ok and cd_ok and characteristic and skill_not_running:
                actions.append(s.SkillID)
                
        if self_char.items:
            for item_data,count in self_char.items:
                item_enough =  count>0
                item_cd_ok = item_data.CodeID not in self_char.item_cooldowns  # 沒在CD才能放
                item_buff_not_running = item_data.CodeID not in self_char.buff_item  # 若是buff且沒再運作中
                if item_enough and item_cd_ok and item_buff_not_running:
                    actions.append(f"USE_ITEM:{item_data.CodeID}")

        # === ε-greedy 策略 ===
        if random.random() < self.epsilon:
            action = random.choice(actions)
        else:
            q_values = []
            for a in actions:
                base = self.Q.get((state, a), 0.0)
                # 技能動作加 bias（例如 +0.5）
                if a != "NORMAL_ATTACK" and not a.startswith("USE_ITEM"):
                    base += 0.5
                q_values.append(base)
            action = actions[q_values.index(max(q_values))]
        
        #if(self_char.characterType):
            #print(f"[AI] 狀態={state} → 選擇動作={action}")
        return action, state
    
    def update_q(self, state, action, reward, next_state):
        """
        更新 Q-table
        """
        old_q = self.Q.get((state, action), 0.0)
        next_q = max(
            (self.Q.get((next_state, a), 0.0) for a in self.Q if a[0] == next_state),
            default=0.0
        ) if next_state else 0.0

        self.Q[(state, action)] = old_q + self.alpha * (reward + self.gamma * next_q - old_q)
        # print("目前 Q 表紀錄數量：", len(self.Q))
        self.save_q_table()