from typing import Callable, List

class Event:
    def __init__(self):
        self._subscribers: List[Callable] = []

    def __iadd__(self, subscriber: Callable):
        """模擬 C# +="""
        self._subscribers.append(subscriber)
        return self

    def __isub__(self, subscriber: Callable):
        """模擬 C# -="""
        if subscriber in self._subscribers:
            self._subscribers.remove(subscriber)
        return self

    def __call__(self, *args, **kwargs):
        """模擬 C# Invoke()"""
        for sub in list(self._subscribers):  # 用 list() 避免迴圈中移除問題
            sub(*args, **kwargs)

    def clear(self):
        """清空所有訂閱者"""
        self._subscribers.clear()