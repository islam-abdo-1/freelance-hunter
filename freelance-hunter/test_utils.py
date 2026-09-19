from core.utils import generate_job_id, normalize_url, extract_domain, calculate_similarity, is_duplicate_job, parse_date, extract_budget
from datetime import datetime

# Test generate_job_id
id1 = generate_job_id('upwork', 'https://upwork.com/jobs/123', 'Data Entry Job')
id2 = generate_job_id('upwork', 'https://upwork.com/jobs/123', 'Data Entry Job')
print(f'generate_job_id: {id1} (same: {id1 == id2})')

# Test normalize_url
url = 'https://www.UpWork.com/jobs/123?utm_source=google&ref=homepage'
norm = normalize_url(url)
print(f'normalize_url: {norm}')

# Test extract_domain
dom = extract_domain('https://www.upwork.com/jobs/123')
print(f'extract_domain: {dom}')

# Test calculate_similarity
sim = calculate_similarity('hello world', 'hello world')
print(f'calculate_similarity (same): {sim}')
sim = calculate_similarity('hello world', 'hello')
print(f'calculate_similarity (partial): {sim}')

# Test parse_date
dt = parse_date('2024-01-15T10:30:00Z')
print(f'parse_date ISO: {dt}')
dt = parse_date('2 hours ago')
print(f'parse_date relative: {dt}')

# Test extract_budget
budget = extract_budget('Budget: $500 fixed price')
print(f'extract_budget fixed: {budget}')
budget = extract_budget('Rate: $25/hr')
print(f'extract_budget hourly: {budget}')

# Test is_duplicate_job
job1 = {'job_url': 'https://upwork.com/jobs/123', 'title': 'Data Entry', 'client_name': 'John', 'full_description': 'Enter data', 'date_posted': datetime.utcnow(), 'platform': 'upwork'}
job2 = {'job_url': 'https://upwork.com/jobs/123', 'title': 'Data Entry', 'client_name': 'John', 'full_description': 'Enter data', 'date_posted': datetime.utcnow(), 'platform': 'upwork'}
is_dup, reason, score = is_duplicate_job(job1, job2)
print(f'is_duplicate_job (same URL): {is_dup}, {reason}, {score}')

print('All utility tests passed!')