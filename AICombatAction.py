import random
from collections import defaultdict
from game_models import GameData

class ai_action:
    def __init__(self, skills,item):
        self.skills = skills
        self.item = item
        self.Q = defaultdict(float)  # Q表
        self.alpha = 0.1  # 學習率
        self.gamma = 0.9  # 折扣因子
        self.epsilon = 0.2  # 探索率

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
            cooldown_features.append(remaining_time / max_time)


        # 可以加更多資訊，如buff狀態
        return tuple(list(state)+buff_features+cooldown_features)

    def choose_action(self, self_char, enemy):
        state = self.get_state(self_char, enemy)

        # === 合法動作清單 ===
        actions = ["NORMAL_ATTACK"]
        for s in self.skills:
            characteristic = s.Characteristic
            mp_ok = self_char.stats["MP"] >= s.CastMage
            cd_ok = s.SkillID not in self_char.skill_cooldowns  # 沒在CD才能放
            if mp_ok and cd_ok and characteristic:
                actions.append(s.SkillID)
                
        if self_char.items:
            for item_data,count in self_char.items:
                if(count>0):
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
        
        if(self_char.characterType):
            print(f"[AI] 狀態={state} → 選擇動作={action}")
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