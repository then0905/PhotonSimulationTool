from dataclasses import dataclass

@dataclass
class CharacterStatus_Core:
    """
    主要能力值
    """
    MeleeATK: int = 0  # 近戰攻擊力
    RemoteATK: int = 0  # 遠程攻擊力
    MageATK: int = 0  # 魔法攻擊力
    MaxHP: int = 0  # 最大生命值
    HP: int = 0  # 當前生命值
    MaxMP: int = 0  # 最大魔法值
    MP: int = 0  # 當前魔法值
    DEF: int = 0  # 物理防禦力
    Avoid: int = 0  # 迴避率
    MeleeHit: int = 0  # 近戰命中率
    RemoteHit: int = 0  # 遠程命中率
    MageHit: int = 0  # 魔法命中率
    MDEF: int = 0  # 魔法防禦力
    Speed: float = 0  # 移動速度
    AS: int = 0  # 攻擊速度 (Attack Speed)
    DamageReduction: int = 0  # 傷害減免
    ElementDamageIncrease: int = 0  # 元素傷害增加
    ElementDamageReduction: int = 0  # 元素傷害減免
    HP_Recovery: int = 0  # 生命值回復
    MP_Recovery: int = 0  # 魔法值回復
    Crt: int = 0  # 暴擊
    CrtResistance: int = 0  # 暴擊抵抗
    CrtDamage: int = 0  # 暴擊附加傷害
    BlockRate: int = 0  # 格檔率
    DisorderResistance: int = 0  # 異常狀態抗性

@dataclass
class CharacterStatus_Secret:
    """
    隱密能力值
    """
    IncreaseDmgRate:float = 0 #傷害增加(倍率)
    IncreaseDmgValue:int = 0 #傷害增加(值)
    RecoveryDmgRate:float = 0 #減少受到傷害(倍率)
    RecoveryDmgValue:int = 0 #減少受到傷害(值)
    Damage:float = 0 #總傷害(傷害公式計算完成後乘上)
    
@dataclass
class CharacterStatus_Debuff:
    """
    負面影響能力值
    """
    SpeedSlow: float = 0  # 移動速度
    
@dataclass
class CharacterStatus_Element:
    """
    屬性方面能力值
    """
    HolyDamage: int = 0  # 神聖屬性傷害