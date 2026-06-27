import subprocess
import os

os.chdir(r'E:\量化研究\workspace\stock')

result = subprocess.run(
    ['E:\\量化研究\\workspace\\stock\\.venv\\bin\\python3', 'check_env.py'],
    capture_output=True,
    text=True,
    timeout=30
)

with open('result.txt', 'w', encoding='utf-8') as f:
    f.write(f"STDOUT:\n{result.stdout}\n")
    f.write(f"STDERR:\n{result.stderr}\n")
    f.write(f"RETURN CODE: {result.returncode}\n")
    f.write(f"PYTHON: {result.args}\n")

print("Done writing result.txt")
