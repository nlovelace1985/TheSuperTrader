# -*- coding: utf-8 -*-
"""
Created on Sun Aug  4 12:27:17 2024

@author: prave
"""

import random
import string

def generate_random_text(length=16):
    characters = string.ascii_letters + string.digits
    random_text = ''.join(random.choice(characters) for _ in range(length))
    return random_text

# Example usage
random_text = generate_random_text()
print(random_text)
