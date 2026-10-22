"""Find all triple-quoted strings in similarity.py that cause Python 3.14 parse issues."""
import re

with open("app/ai/similarity.py", encoding="utf-8") as f:
    content = f.read()

lines = content.split("\n")

# Find which line causes the first compile failure by binary search
def compiles_up_to(n):
    partial = "\n".join(lines[:n])
    try:
        compile(partial + "\n", "similarity.py", "exec")
        return True
    except SyntaxError as e:
        if "unterminated" in str(e):
            return False
        return True  # different error, not our problem

lo, hi = 1, len(lines)
first_bad = None
while lo < hi:
    mid = (lo + hi) // 2
    if compiles_up_to(mid):
        lo = mid + 1
    else:
        first_bad = mid
        hi = mid

print(f"First problematic line: {first_bad}")
if first_bad:
    # Print surrounding context
    for i in range(max(0, first_bad - 10), min(len(lines), first_bad + 3)):
        print(f"  {i+1}: {repr(lines[i])}")
