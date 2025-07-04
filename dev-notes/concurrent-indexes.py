#!/usr/bin/env python3

import gel


def create_concurrent_indexes(db, msg_callback=print):
    '''Actually create all "create concurrently" indexes

    The protocol here is to find all the indexes that need created,
    and create them with `administer concurrent_index_build()`.
    It's possible that the database will shut down after an index
    creation but before the metadata is updated, in which case
    we might rerun the command later, which is harmless.

    If we stick with this ADMINISTER-based schemed, I figure this code
    would live in the CLI.
    '''
    indexes = db.query('''
        select schema::Index {
            id, expr, subject_name := .<indexes[is schema::ObjectType].name
        }
        filter .build_concurrently and not .active
    ''')
    for index in indexes:
        msg_callback(
            f"Creating concurrent index on '{index.subject_name}' "
            f"with expr ({index.expr})"
        )
        db.execute(f'''
            administer concurrent_index_build("<uuid>{index.id}")
        ''')


def main():
    with gel.create_client() as db:
        create_concurrent_indexes(db)


if __name__ == '__main__':
    main()
