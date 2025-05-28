#!/usr/bin/env python3

import gel

def create_concurrent_indexes(db):
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
        print(
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
