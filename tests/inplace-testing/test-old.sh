#!/bin/bash -ex

while [[ $# -gt 0 ]]; do
  case $1 in
    --rollback-and-test)
        ROLLBACK=1
        shift
        ;;
    --rollback-and-reapply)
        REAPPLY=1
        shift
        ;;
    --save-tarballs)
        SAVE_TARBALLS=1
        shift
        ;;
    *)
        break
        ;;
  esac
done


DIR="$1"
RDIR=$(realpath "$1")
SERVER_INSTALL=$(realpath "$2")
shift 2

# Force bootstrapping of the server
TMPDIR=$(mktemp -d)
edb server --bootstrap-only --data-dir $TMPDIR/bootstrap || (rm -rf $TMPDIR && false)

# Setup the test database
(cd / && GEL_SERVER_SECURITY=insecure_dev_mode $SERVER_INSTALL/bin/python3  -m edb.tools --no-devmode inittestdb --tests-dir $SERVER_INSTALL/share/tests -k test_dump --data-dir "$RDIR")


if [ "$SAVE_TARBALLS" = 1 ]; then
    tar cf "$DIR".tar "$DIR"
fi


PORT=$(( $RANDOM + 2000 ))
GEL_SERVER_SECURITY=insecure_dev_mode $SERVER_INSTALL/bin/gel-server --testmode -D "$RDIR" -P $PORT &
SPID=$!
stop_server() {
    kill $SPID
    wait $SPID
    SPID=
}
cleanup() {
    if [ -n "$SPID" ]; then
        stop_server
    fi
}
trap cleanup EXIT

GEL="gel -H localhost -P $PORT --tls-security insecure --wait-until-available 120sec"

# Wait for the server to come up and see it is working
$GEL -b dump01 query 'select count(Z)' | grep 2

# Block DDL
$GEL query 'configure instance set force_database_error := $${"type": "AvailabilityError", "message": "DDL is disabled due to in-place upgrade.", "_scopes": ["ddl"]}$$;'

if $GEL query 'create empty branch asdf'; then
    echo Unexpected DDL success despite blocking it
    exit 4
fi

# Prepare the upgrades
EDGEDB_PORT=$PORT EDGEDB_CLIENT_TLS_SECURITY=insecure python3 tests/inplace-testing/prep-upgrades.py > "${DIR}/upgrade.json"

if [ "$SAVE_TARBALLS" = 1 ]; then
    tar cf "$DIR"-ready.tar "$DIR"
fi

# Get the DSN from the debug endpoint
DSN=$(curl -s http://localhost:$PORT/server-info | jq -r '.pg_addr.dsn')

# Prepare the upgrade, operating against the postgres that the old
# version server is managing
edb server --inplace-upgrade-prepare "$DIR"/upgrade.json --backend-dsn="$DSN"

# Check the server is still working
$GEL -b dump01 query 'select count(Z)' | grep 2

if [ "$ROLLBACK" = 1 ]; then
    # Inject a failure into our first attempt to rollback
    if EDGEDB_UPGRADE_ROLLBACK_ERROR_INJECTION=dumpbasics edb server --inplace-upgrade-rollback --backend-dsn="$DSN"; then
        echo Unexpected rollback success despite failure injection
        exit 4
    fi

    # Second try should work
    edb server --inplace-upgrade-rollback --backend-dsn="$DSN"
    $GEL query 'configure instance reset force_database_error'

    # XXX: what can we do here???
    stop_server
    # patch -R -f -p1 < tests/inplace-testing/upgrade.patch
    # make parsers
    # edb test --data-dir "$DIR" --use-data-dir-dbs -v "$@"
    exit 0
fi

if [ "$REAPPLY" = 1 ]; then
    # Rollback and then reapply
    edb server --inplace-upgrade-rollback --backend-dsn="$DSN"

    edb server --inplace-upgrade-prepare "$DIR"/upgrade.json --backend-dsn="$DSN"
fi

# Check the server is still working
$GEL -b dump01 query 'select count(Z)' | grep 2

# Kill the old version so we can finalize the upgrade
stop_server

if [ "$SAVE_TARBALLS" = 1 ]; then
    tar cf "$DIR"-prepped.tar "$DIR"
fi

# Try to finalize the upgrade, but inject a failure
if EDGEDB_UPGRADE_FINALIZE_ERROR_INJECTION=dumpbasics edb server --inplace-upgrade-finalize --data-dir "$DIR"; then
    echo Unexpected upgrade success despite failure injection
    exit 4
fi

# Try doing a rollback. It should fail, because of the partially
# succesful finalization.
if edb server --inplace-upgrade-rollback --data-dir "$DIR"; then
    echo Unexpected upgrade success
    exit 5
fi

# Finalize the upgrade
edb server --inplace-upgrade-finalize --data-dir "$DIR"
if [ "$SAVE_TARBALLS" = 1 ]; then
    tar cf "$DIR"-cooked.tar "$DIR"
fi

# Start the server again so we can reenable DDL
edb server -D "$DIR" -P $PORT &
SPID=$!
if $GEL query 'create empty branch asdf'; then
    echo Unexpected DDL success despite blocking it
    exit 6
fi
$GEL query 'configure instance reset force_database_error'
stop_server
if [ "$SAVE_TARBALLS" = 1 ]; then
    tar cf "$DIR"-cooked2.tar "$DIR"
fi


# Test!
edb test --data-dir "$DIR" --use-data-dir-dbs -v "$@" -k test_dump
