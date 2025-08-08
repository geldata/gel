.. _ref_guide_gel_drizzle:

======================
Drizzle ORM in Next.js
======================

|Gel| integrates seamlessly with Drizzle ORM, providing a type-safe and intuitive way to interact with your database in TypeScript applications.

Enable Drizzle in your Gel project
==================================

.. edb:split-section::

    To integrate Drizzle with your Gel project, you'll need to install the necessary dependencies:

    .. code-block:: bash

        $ npm install drizzle-orm
        $ npm install -D drizzle-kit


.. edb:split-section::

    Next, create a Drizzle configuration file in your project root to tell Drizzle how to work with your Gel database:

    .. code-block:: typescript
        :caption: drizzle.config.ts

        import { defineConfig } from 'drizzle-kit';

        export default defineConfig({
          dialect: 'gel',
        });


Sync your Gel schema with Drizzle
=================================

.. edb:split-section::

    Before using Drizzle with your Gel database, you'll need to let Drizzle introspect your schema. This step generates TypeScript files that Drizzle can use to interact with your database.

    .. code-block:: bash

        $ npx drizzle-kit pull


.. edb:split-section::

    This command will create a schema file based on your Gel database. The file will typically look something like this:

    .. code-block:: typescript
        :caption: drizzle/schema.ts
        :class: collapsible

        import { gelTable, uniqueIndex, uuid, smallint, text, timestamp, relations } from "drizzle-orm/gel-core"
        import { sql } from "drizzle-orm"

        export const books = gelTable("Book", {
          id: uuid().default(sql`uuid_generate_v4()`).primaryKey().notNull(),
          title: text().notNull(),
          author: text(),
          year: smallint(),
          genre: text(),
          read_date: timestamp(),
        }, (table) => [
          uniqueIndex("books_pkey").using("btree", table.id.asc().nullsLast().op("uuid_ops")),
        ]);

        export const notes = gelTable("Note", {
          id: uuid().default(sql`uuid_generate_v4()`).primaryKey().notNull(),
          text: text().notNull(),
          created_at: timestamp().default(sql`datetime_current()`),
          book_id: uuid().notNull(),
        }, (table) => [
          uniqueIndex("notes_pkey").using("btree", table.id.asc().nullsLast().op("uuid_ops")),
        ]);


Keep Drizzle in sync with Gel
=============================

.. edb:split-section::

    To keep your Drizzle schema in sync with your Gel schema, add a hook to your ``gel.toml`` file. This hook will automatically run ``drizzle-kit pull`` after each migration:

    .. code-block:: toml
        :caption: gel.toml

        [hooks]
        after_migration_apply = [
          "npx drizzle-kit pull"
        ]



With this hook in place, your Drizzle schema will automatically update whenever you apply Gel migrations.


Create a database client
========================

.. edb:split-section::

    Now, let's create a database client that you can use throughout your application:

    .. code-block:: typescript
        :caption: src/db/index.ts

        import { drizzle } from 'drizzle-orm/gel';
        import { createClient } from 'gel-js';
        import * as schema from '@/drizzle/schema';
        import * as relations from '@/drizzle/relations';

        // Import our schema
        import * as schema from './schema';

        // Initialize Gel client
        const gelClient = createClient();

        // Create Drizzle instance
        export const db = drizzle({
          client: gelClient,
          schema: {
            ...schema,
            ...relations
          },
        });

        // Helper types for use in our application
        export type Book = typeof schema.book.$inferSelect;
        export type NewBook = typeof schema.book.$inferInsert;

        export type Note = typeof schema.note.$inferSelect;
        export type NewNote = typeof schema.note.$inferInsert;


Perform database operations with Drizzle
========================================

For more detailed information on querying and other operations, refer to the `Drizzle documentation <https://orm.drizzle.team/docs/rqb>`_. Below are some examples of common database operations you can perform with Drizzle.

.. edb:split-section::

    Drizzle provides a clean, type-safe API for database operations. Here are some examples of common operations:

    **Selecting data:**

    .. code-block:: typescript

        // Get all books with their notes
        const allBooks = await db.query.book.findMany({
          with: {
            notes: true,
          },
        });

        // Get a specific book
        const book = await db.query.book.findFirst({
          where: eq(books.id, id),
          with: { notes: true },
        });


.. edb:split-section::

    **Inserting data:**

    .. code-block:: typescript

      // Insert a new book
      const newBook = await db.insert(book).values({
        title: 'The Great Gatsby',
        author: 'F. Scott Fitzgerald',
        year: 1925,
        genre: 'Novel',
      }).returning();

      // Insert a note for a book
      const newNote = await db.insert(note).values({
        text: 'A classic novel about the American Dream',
        book_id: newBook.bookId,
      }).returning();

    **Bulk inserting data:**

    .. code-block:: typescript

      // Insert multiple books at once
      const newBooks = await db.insert(book).values([
        {
          title: '1984',
          author: 'George Orwell',
          year: 1949,
          genre: 'Dystopian',
        },
        {
          title: 'To Kill a Mockingbird',
          author: 'Harper Lee',
          year: 1960,
          genre: 'Fiction',
        },
        {
          title: 'Pride and Prejudice',
          author: 'Jane Austen',
          year: 1813,
          genre: 'Romance',
        },
      ]).returning();

.. edb:split-section::

    **Updating data:**

    .. code-block:: typescript

        // Update a book
        const updatedBook = await db.update(book)
          .set({
            title: 'Updated Title',
            author: 'Updated Author',
          })
          .where(eq(books.id, bookId))
          .returning();


.. edb:split-section::

    **Deleting data:**

    .. code-block:: typescript

        // Delete a note
        await db.delete(notes).where(eq(notes.id, noteId));


Using Drizzle with Next.js
==========================

.. edb:split-section::

    In a Next.js application, you can use your Drizzle client in API routes and server components. Here's an example of an API route that gets all books:

    .. code-block:: typescript
        :caption: src/app/api/books/route.ts

        import { NextResponse } from 'next/server';
        import { db } from '@/db';

        export async function GET() {
          try {
            const allBooks = await db.query.book.findMany({
              with: { notes: true },
            });

            return NextResponse.json(allBooks);
          } catch (error) {
            console.error('Error fetching books:', error);
            return NextResponse.json(
              { error: 'Failed to fetch books' },
              { status: 500 }
            );
          }
        }


.. edb:split-section::

    And here's an example of using Drizzle in a server component:

    .. code-block:: typescript
        :caption: src/app/books/page.tsx

        import { db } from '@/db';
        import BookCard from '@/components/BookCard';

        export default async function BooksPage() {
          const books = await db.query.book.findMany({
            with: { notes: true },
          });

          return (
            <div>
              {books.map((book) => (
                <BookCard key={book.id} book={book} />
              ))}
            </div>
          );
        }


Keep going!
===========

You are now ready to use Gel with Drizzle in your applications. This integration gives you the best of both worlds: Gel's powerful features and Drizzle's type-safe, intuitive API.

For a complete example of using Gel with Drizzle in a Next.js application, check out our `Book Notes app example <https://github.com/geldata/gel-examples/tree/main/drizzle-book-notes-app>`_.

You can also find a detailed tutorial on building a Book Notes app with Gel, Drizzle, and Next.js in our :ref:`documentation <ref_guide_gel_drizzle_booknotes>`.
