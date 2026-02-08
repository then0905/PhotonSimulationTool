import matplotlib.pyplot as plt
import seaborn as sns
from typing import List, Dict
from commonfunction import get_text

class StatsAnalyzer:
    # seaborn通常對中文支援較好
    sns.set_style("whitegrid")
    plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei']
    
    @staticmethod
    def plot_damage_distribution(damage_data: List[Dict], title="傷害分布"):
        damages = [d["Damage"] for d in damage_data]
        plt.figure(figsize=(10, 5))
        plt.hist(damages, bins=20, alpha=0.7)
        plt.title(title)
        plt.xlabel("傷害值")
        plt.ylabel("出現次數")
        plt.grid(True)
        plt.show()

    @staticmethod
    def plot_skill_usage(
            player_skill_usage: Dict[str, int],
            enemy_skill_usage: Dict[str, int],
            title="技能使用頻率"
    ):
        # 玩家資料
        player_skills = list(player_skill_usage.keys())
        player_counts = list(player_skill_usage.values())

        # 敵人資料
        enemy_skills = [get_text(s) for s in enemy_skill_usage.keys()]
        enemy_counts = list(enemy_skill_usage.values())

        plt.figure(figsize=(14, 5))  # 只開一次

        # 左圖：玩家
        plt.subplot(1, 2, 1)
        plt.bar(player_skills, player_counts, alpha=0.7)
        plt.title("玩家技能使用")
        plt.xlabel("技能名稱")
        plt.ylabel("使用次數")
        plt.xticks(rotation=45)
        plt.grid(True)

        # 右圖：敵人
        plt.subplot(1, 2, 2)
        plt.bar(enemy_skills, enemy_counts, alpha=0.7)
        plt.title("敵人技能使用")
        plt.xlabel("技能名稱")
        plt.ylabel("使用次數")
        plt.xticks(rotation=45)
        plt.grid(True)

        plt.suptitle(title)
        plt.tight_layout()
        plt.show()

    @staticmethod
    def calculate_win_rate(results: List[bool]) -> float:
        if not results:
            return 0.0
        return sum(results) / len(results)