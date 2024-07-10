# -*- coding: utf-8 -*-
"""
Created on Mon Jul  8 10:58:36 2024
@author: TST
"""

import os
import requests
import subprocess


# GITHUB_REPO_URL = "https://raw.githubusercontent.com/bpraveenX/TST_1_SrcCode/main/tst_v6_local.py"
# LOCAL_SCRIPT_PATH = "tst_v_n2.py"

# Function to download the latest script
def download_latest_script():
    try:
        print('trying loop1')
        response = requests.get(GITHUB_REPO_URL)
        response.raise_for_status()
        # print(response.text)
        with open(LOCAL_SCRIPT_PATH, 'w') as file:
            file.write(response.text)
        # messagebox.showinfo("Success", "Script updated successfully!")
    except Exception as e:
        print(e)
        # messagebox.showerror("Error", f"Failed to download the script: {e}")

# Function to run the script
def run_script():
    try:
        subprocess.run(["python", LOCAL_SCRIPT_PATH])
    except Exception as e:
        print(e)
        # messagebox.showerror("Error", f"Failed to run the script: {e}")

# Create the main application window
# download_latest_script()

GITHUB_REPO_URL = "https://raw.githubusercontent.com/nlovelace1985/TheSuperTrader/main/TST_NextGenAlgo_Live.py"
LOCAL_SCRIPT_PATH = "TST_NextGenAlgo_Live.py"
download_latest_script()
