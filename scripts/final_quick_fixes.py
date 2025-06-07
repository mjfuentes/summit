#!/usr/bin/env python3

import re

# Fix SQLAlchemy import order in database.py
with open("src/database.py", "r") as f:
    content = f.read()

# Fix alphabetical order
content = re.sub(
    r"from sqlalchemy import \(\s*Boolean,\s*Column,\s*DateTime,\s*Integer,\s*JSON,\s*String,\s*Text,\s*delete,\s*func,\s*select,\s*update,\s*\)",
    """from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    JSON,
    String,
    Text,
    delete,
    func,
    select,
    update,
)""",
    content,
    flags=re.DOTALL,
)

with open("src/database.py", "w") as f:
    f.write(content)

print(" Fixed SQLAlchemy imports")

# Fix remaining bare except in summit.py
with open("src/summit.py", "r") as f:
    content = f.read()

# Fix bare except clause
content = content.replace("        except:", "        except Exception:")

# Fix a few simple line length issues
fixes = [
    (
        'url = f"https://api.github.com/repos/{owner}/{repo}/codespaces"',
        'url = f"https://api.github.com/repos/{owner}/{repo}/codespaces"',
    ),
    (
        '"Provide AI-powered advice and guidance for development and coding questions"',
        '"AI-powered advice and guidance for development questions"',
    ),
    (
        '"Get current Summit status, uptime, and cost information"',
        '"Get Summit status, uptime, and cost information"',
    ),
]

for old, new in fixes:
    if old in content and len(new) <= 79:
        content = content.replace(old, new)

with open("src/summit.py", "w") as f:
    f.write(content)

print(" Fixed summit.py issues")

print("Done!")
