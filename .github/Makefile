.PHONY: all

ROOT = $(dir $(realpath $(firstword $(MAKEFILE_LIST))))

all: \
	workflows/build.nightly.yml \
	workflows/build.release.yml \
	workflows/build.testing.yml \
	workflows/build.dryrun.yml \
	workflows/build.ls-nightly.yml \
	workflows/tests.yml \
	workflows/tests.pool.yml \
	workflows/tests.managed-pg.yml \
	workflows/tests.ha.yml \
	workflows/tests.pg-versions.yml \
	workflows/tests.patches.yml \
	workflows/tests.inplace.yml \
	workflows/tests.inplace7x.yml \
	workflows/tests.reflection.yml \

workflows/build.%.yml: workflows.src/build.%.tpl.yml workflows.src/build.%.targets.yml workflows.src/build.inc.yml
	$(ROOT)/workflows.src/render.py --workflow=build build.$* build.$*.targets.yml

workflows/tests.yml: workflows.src/tests.tpl.yml workflows.src/tests.targets.yml workflows.src/tests.inc.yml
	$(ROOT)/workflows.src/render.py --workflow=test tests tests.targets.yml

workflows/tests.%.yml: workflows.src/tests.%.tpl.yml workflows.src/tests.%.targets.yml workflows.src/tests.inc.yml
	$(ROOT)/workflows.src/render.py --workflow=test tests.$* tests.$*.targets.yml
