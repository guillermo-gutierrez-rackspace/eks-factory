import sys, json

role_arn = sys.argv[1]

aws_auth = json.loads(sys.stdin.read())

with open('aws-auth.json.template') as f:
  aws_auth_patch = json.loads(f.read())

aws_auth_patch['data'] = {}

with open('role.yml.template') as f:
  aws_auth_patch['data']['mapRoles'] = aws_auth['data']['mapRoles'].replace(f.read().replace('ROLE-ARN', role_arn), '')

aws_auth_patch['data']['mapUsers'] = aws_auth['data']['mapUsers']

sys.stdout.write(json.dumps(aws_auth_patch))