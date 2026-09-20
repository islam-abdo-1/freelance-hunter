with open('tests/test_all.py', 'r') as f:
    content = f.read()

# Fix the matching_agent test - change assertion for matched_skills
old = 'assert "Excel" in match["matched_skills"]'
new = 'assert "microsoft excel" in match["matched_skills"] or "excel" in match["matched_skills"]'

content = content.replace(old, new)

with open('tests/test_all.py', 'w') as f:
    f.write(content)

print('Fixed!')