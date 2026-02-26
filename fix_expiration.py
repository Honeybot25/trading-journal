import re

with open('spy_gex_bot.py', 'r') as f:
    content = f.read()

old_code = '''        if expiration is None:
            # Use nearest expiration
            expirations = spy.options
            expiration = expirations[0] if expirations else None'''

new_code = '''        if expiration is None:
            # Use nearest expiration with at least 1 day remaining
            expirations = spy.options
            today = datetime.now().date()
            expiration = None
            for exp in expirations:
                exp_date = datetime.strptime(exp, '%Y-%m-%d').date()
                days_to_exp = (exp_date - today).days
                if days_to_exp >= 1:
                    expiration = exp
                    break'''

content = content.replace(old_code, new_code)

with open('spy_gex_bot.py', 'w') as f:
    f.write(content)

print("Fixed!")
