with open('tests/test_all.py', 'r') as f:
    content = f.read()

# Fix the platform_model test
old = '''        platform = Platform(
            name="Test Platform",
            url="https://test.com",
            jobs_url="https://test.com/jobs",
            category="test",
            country_region="global",
            login_required=False,
            public_access=True
        )'''

new = '''        platform = Platform(
            name="Test Platform",
            url="https://test.com",
            jobs_url="https://test.com/jobs",
            category="test",
            country_region="global",
            login_required=False,
            public_access=True,
            is_active=True
        )'''

content = content.replace(old, new)

with open('tests/test_all.py', 'w') as f:
    f.write(content)

print('Fixed!')