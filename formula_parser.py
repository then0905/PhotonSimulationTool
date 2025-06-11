import random
import re
import math
from typing import Dict

class FormulaParser:
    def __init__(self):
        self.variables: Dict[str, float] = {}
        self.functions = {
            'sqrt': math.sqrt,
            'pow': math.pow,
            'min': min,
            'max': max,
            'rand': lambda a, b: a + (b-a) * random.random()
        }
    
    def set_variables(self, variables: Dict[str, float]):
        self.variables = variables
    
    def evaluate(self, formula: str) -> float:
        try:
            # 替換變量
            for var, val in self.variables.items():
                formula = re.sub(rf'\b{var}\b', str(val), formula)
            
            # 檢查安全性
            if not self._is_safe(formula):
                raise ValueError("Formula contains unsafe code")
            
            # 評估表達式
            return eval(formula, {"__builtins__": None}, self.functions)
        except Exception as e:
            print(f"Error evaluating formula: {formula}")
            raise e
    
    def _is_safe(self, formula: str) -> bool:
        # 簡單的安全性檢查
        unsafe = ["import", "exec", "eval", "open", "__"]
        return not any(word in formula for word in unsafe)