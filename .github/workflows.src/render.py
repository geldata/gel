#!/usr/bin/env python3

import argparse
import pathlib
import sys

import jinja2
import yaml


env = jinja2.Environment(
    variable_start_string='<<',
    variable_end_string='>>',
    block_start_string='<%',
    block_end_string='%>',
    loader=jinja2.FileSystemLoader(pathlib.Path(__file__).parent),
)


def die(msg):
    print(msg, file=sys.stderr)
    sys.exit(1)


def _expand_test_spec(target):
    if "test" not in target:
        target["test"] = {
            "include": "",
            "exclude": "",
            "files": ""
        }

    for key in {"include", "exclude", "files"}:
        if key not in target["test"]:
            target["test"][key] = ""


def _render(tpl_path, data):
    with open(tpl_path) as f:
        tpl = env.from_string(f.read())

    return tpl.render(**data)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workflow', choices=["build", "test"], required=True)
    parser.add_argument('template')
    parser.add_argument('datafile')

    args = parser.parse_args()

    tplfile = f'{args.template}.tpl.yml'
    path = pathlib.Path(__file__).parent / tplfile

    if not path.exists():
        die(f'template does not exist: {tplfile}')

    datapath = pathlib.Path(__file__).parent / args.datafile

    if datapath.exists():
        with open(datapath) as f:
            data = yaml.load(f, Loader=yaml.SafeLoader)
    else:
        data = {}

    if args.workflow == "build":
        package = data.get("package")
        if not package or not isinstance(package, dict):
            die(f"invalid package: specification in {datapath}")
        if not package.get("name"):
            die(f"missing package.name in {datapath}")

        _expand_test_spec(package)

        targets = data.get("targets")
        if not targets or not isinstance(targets, dict):
            die(f"invalid targets: specification in {datapath}")

        for target_list in targets.values():
            for target in target_list:
                _expand_test_spec(target)

    output = _render(path, data)

    target = (
        pathlib.Path(__file__).parent.parent
        / 'workflows'
        / f'{args.template}.yml'
    )
    with open(target, 'w') as f:
        print(output, file=f)


if __name__ == '__main__':
    main()
