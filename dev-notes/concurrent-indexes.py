#!/usr/bin/env python3

import gel

def create_concurrent_indexes(db, msg_callback=print):
    '''Actually create all "create concurrently" indexes

    The protocol here is to call `administer concurrent_index_update()`
    to make sure that the `active` properties match database reality
    (since concurrent_index_create can't update them atomically),
    then find all the indexes that need created,
    create them with `administer concurrent_index_create()`,
    and then run `administer concurrent_index_update()` again.

    If we stick with this ADMINISTER-based schemed, I figure this code
    would live in the CLI.
    '''
    db.execute('''
        administer concurrent_index_update();
    ''')
    indexes = db.query('''
        select schema::Index {
            id, expr, subject_name := .<indexes[is schema::ObjectType].name
        }
        filter .create_concurrently and not .active
    ''')
    for index in indexes:
        msg_callback(
            f"Creating concurrent index on '{index.subject_name}' "
            f"with expr ({index.expr})"
        )
        db.execute(f'''
            administer concurrent_index_create("{index.id}")
        ''')
    db.execute('''
        administer concurrent_index_update();
    ''')


def main():
    with gel.create_client() as db:
        create_concurrent_indexes(db)


if __name__ == '__main__':
    main()
