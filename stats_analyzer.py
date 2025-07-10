import matplotlib.pyplot as plt
import seaborn as sns
from typing import List, Dict
from commonfunction import CommonFunction

class StatsAnalyzer:
    # seaborn通常對中文支援較好
    sns.set_style("whitegrid")
    plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei']
    
    @staticmethod
    def plot_damage_distribution(damage_data: List[Dict], title="傷害分布"):
        damages = [d["damage"] for d in damage_data]
        plt.figure(figsize=(10, 5))
        plt.hist(damages, bins=20, alpha=0.7)
        plt.title(title)
        plt.xlabel("傷害值")
        plt.ylabel("出現次數")
        plt.grid(True)
        plt.show()
    
    @staticmethod
    def plot_skill_usage(skill_usage: Dict[str, int], title="技能使用頻率"):
        skills = list()
        for skill in list(skill_usage.keys()):
            skills.append(CommonFunction.get_text(skill));
        counts = list(skill_usage.values())
        
        plt.figure(figsize=(10, 5))
        plt.bar(skills, counts, alpha=0.7)
        plt.title(title)
        plt.xlabel("技能名稱")
        plt.ylabel("使用次數")
        plt.xticks(rotation=45)
        plt.grid(True)
        plt.show()
    
    @staticmethod
    def calculate_win_rate(results: List[bool]) -> float:
        if not results:
            return 0.0
        return sum(results) / len(results)