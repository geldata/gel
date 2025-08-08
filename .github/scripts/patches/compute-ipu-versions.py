# Compute prior minor versions to test upgrading from


import json
import os
import pathlib
import re
import sys
from urllib import request

sys.path.append(str(pathlib.Path(__file__).parent.parent.parent.parent))

import edb.buildmeta

base = 'https://packages.geldata.com'
u = f'{base}/archive/.jsonindexes/x86_64-unknown-linux-gnu.json'
data = json.loads(request.urlopen(u).read())

u = f'{base}/archive/.jsonindexes/x86_64-unknown-linux-gnu.testing.json'
data_testing = json.loads(request.urlopen(u).read())

version = edb.buildmeta.EDGEDB_MAJOR_VERSION - 1

versions = []
prerelease_versions = []
for obj in data['packages'] + data_testing['packages']:
    if (
        obj['basename'] == 'gel-server'
        and obj['version_details']['major'] == version
        and (
            not obj['version_details']['prerelease']
            or obj['version_details']['prerelease'][0]['phase'] in ('beta', 'rc')
        )
    ):
        l = (
            versions if not obj['version_details']['prerelease']
            else prerelease_versions
        )
        l.append((
            obj['version'],
            obj['basename'],
            base + obj['installrefs'][0]['ref'],
        ))

if not versions:
    versions = prerelease_versions

versions.sort(key=lambda x: x[0])
if len(versions) > 3:
    # We want to try 6.0 and 6.2
    versions = [versions[0], versions[2], versions[-1]]
elif len(versions) > 1:
    versions = [versions[0], versions[-1]]

matrix = {
    "include": [
        {"edgedb-version": v, "edgedb-url": url, "edgedb-basename": base}
        for v, base, url in versions
    ]
}

print("matrix:", matrix)
if output := os.getenv('GITHUB_OUTPUT'):
    with open(output, 'a') as f:
        print(f'matrix={json.dumps(matrix)}', file=f)
