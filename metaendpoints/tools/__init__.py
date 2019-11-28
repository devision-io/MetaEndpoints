import os
import subprocess


def exec_cmd(cmd, check=True):
    print("Ran cmd:")
    print(cmd)
    subprocess.run(cmd, shell=True, check=check)


os.chdir(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.getcwd()
