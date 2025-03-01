# Test downgrading a database after an upgrade

import edgedb

import json
import os
import subprocess
import sys

cmd = [
    sys.argv[1], '-D' 'test-dir',
    '--testmode', '--security', 'insecure_dev_mode', '--port', '10000',
]
proc = subprocess.Popen(cmd)

db = edgedb.create_client(
    host='localhost', port=10000, tls_security='insecure',
    database='policies',
)

try:
    # Test that a basic query works
    res = json.loads(db.query_json('''
        select Issue { name, number, watchers: {name} }
        filter .number = "1"
    '''))
    expected = [{
        "name": "Release EdgeDB",
        "number": "1",
        "watchers": [{"name": "Yury"}],
    }]

    assert res == expected, res
finally:
    proc.terminate()
    proc.wait()
