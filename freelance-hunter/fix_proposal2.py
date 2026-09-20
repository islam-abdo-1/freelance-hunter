with open('tests/test_all.py', 'r') as f:
    content = f.read()

# Fix the proposal_agent test - add match_level to the job
old = '''        job = {
            "job_id": "test1",
            "title": "Excel Data Entry Specialist",
            "full_description": "Need someone to enter data from invoices into Excel spreadsheets.",
            "matched_skills": ["Excel", "Data Entry"],
            "client_name": "John Client"
        }'''

new = '''        job = {
            "job_id": "test1",
            "title": "Excel Data Entry Specialist",
            "full_description": "Need someone to enter data from invoices into Excel spreadsheets.",
            "matched_skills": ["Excel", "Data Entry"],
            "client_name": "John Client",
            "match_level": "GOOD_MATCH"
        }'''

content = content.replace(old, new)

with open('tests/test_all.py', 'w') as f:
    f.write(content)

print('Fixed!')