.. _ref_guide_gel_drizzle_booknotes:

====================================================
Build a Book Notes App with Drizzle
====================================================

:edb-alt-title: Building a book notes app using Gel, Drizzle ORM, and Next.js

In this tutorial we're going to walk you through building a Book Notes application
that lets you keep track of books you've read along with your personal notes.
We'll be using Gel as the database, Drizzle as the ORM layer, and Next.js as our
full-stack framework.

Gel is a data layer designed to supercharge PostgreSQL with a graph-like object model, access control, Auth, and many other features. It provides a unified schema and tooling experience across multiple languages, making it ideal for projects with diverse tech stacks. With Gel, you get access to EdgeQL, which eliminates n+1 query problems, supports automatic embeddings, and offers a seamless developer experience.

Drizzle, on the other hand, is a TypeScript ORM that offers type safety and a great developer experience. By combining Gel with Drizzle, you can leverage Gel's powerful features while using Drizzle as a familiar ORM layer to interact with your database. This approach is perfect for developers who want to start learning Gel or prefer using Drizzle for their projects.
experience. Next.js is a React framework for building production-ready web applications with features like server components, built-in routing, and API routes. By the end of this tutorial, you will see how these technologies work together to create a modern, full-stack web application with a great developer experience.

.. note::

   The complete source code for this tutorial is available in our `Gel Examples repository
   <https://github.com/geldata/gel-examples/tree/main/drizzle-book-notes-app>`_.


We will start by creating a Gel schema, setting up Drizzle, and then building
a Next.js application with API routes and a simple UI to manage your book collection and notes.


1. Initialize the project
=========================

.. edb:split-section::

  Let's start with setting up our project. We'll create a new Next.js application,
  install the necessary dependencies, and initialize a Gel project.

  Here's a summary of the setup steps we'll follow:

  1. Create a Next.js application
  2. Install Gel and related packages
  3. Initialize a Gel project
  4. Update schema and apply migrations
  5. Install and set up Drizzle
  6. Pull schema into Drizzle
  7. Configure hooks in gel.toml

.. edb:split-section::

  First, let's create a new Next.js application. You can use the
  ``create-next-app`` command to set up a new project. When prompted,
  choose TypeScript, ESLint, Tailwind CSS, and the App Router. You can
  skip the default import alias configuration.
  This will create a new Next.js application with the necessary
  configuration files and dependencies.

  .. note::

    Make sure you have Node.js and npm installed on your machine.

  .. code-block:: bash

      # Step 1: Create a Next.js application
      $ npx create-next-app@latest book-notes-app

      # When prompted, choose:
      # ✔ Would you like to use TypeScript? Yes
      # ✔ Would you like to use ESLint? Yes
      # ✔ Would you like to use Tailwind CSS? Yes
      # ✔ Would you like to use `src/` directory? Yes
      # ✔ Would you like to use App Router? Yes
      # ✔ Would you like to use Turbopack for `next dev`? No
      # ✔ Would you like to customize the default import alias (@/*)? No

      $ cd book-notes-app

.. edb:split-section::

  Next, let's install the Gel library. We'll need ``gel`` for database access.

  .. code-block:: bash

      $ npm i gel

.. edb:split-section::

  Now, we'll initialize a Gel project. This will create the necessary configuration
  files and set up a local Gel instance.

  .. code-block:: bash

      $ npx gel project init

2. Define the Gel schema
========================


Now that we have our project environment set up, let's define our database schema.
For our Book Notes app, we'll create two main types:

1. ``Book`` - to store information about books
2. ``Note`` - to store notes associated with each book

Let's edit the :dotgel:`dbschema/default` file that was created during initialization.

.. edb:split-section::

  Our schema defines two types:

  - ``Book`` with properties like title, author, publication year, genre, and read date.
  - ``Note`` with text content and a timestamp, linked to a specific book.

  The relationship is defined such that a book can have multiple notes, and
  each note belongs to exactly one book. We're using a computed link ``notes`` to
  allow easy access to a book's notes.

  .. code-block:: sdl
      :caption: :dotgel:`dbschema/default`

      module default {
        type Book {
          required title: str;
          author: str;
          year: int16;
          genre: str;
          read_date: datetime;

          # Relationship to notes
          multi notes := .<book[is Note];
        }

        type Note {
          required text: str;
          created_at: datetime {
            default := datetime_current();
          }

          # Link to the book
          required book: Book;
        }
      }

.. edb:split-section::

  Now let's apply this schema to our database by creating and applying a migration:

  .. code-block:: bash

      $ gel migration create
      $ gel migrate


3. Install and set up Drizzle
=============================

Now that we have our Gel schema in place, we can integrate Drizzle ORM with our
Next.js application. Drizzle will provide a type-safe way to interact with our
Gel database.

.. edb:split-section::

  First, let's install Drizzle and its dependencies. We'll need ``drizzle-orm`` and
  ``drizzle-kit`` for this.
  Drizzle ORM is the core library, while Drizzle Kit is a CLI tool that helps
  with schema generation and migrations.

  .. code-block:: bash

      $ npm i drizzle-orm drizzle-kit

.. edb:split-section::

  Let's create a Drizzle configuration file in the root of our project. We'll set the ``dialect`` to ``gel``
  to tell Drizzle that we're using Gel as our database.

  .. code-block:: typescript
      :caption: drizzle.config.ts

      import { defineConfig } from 'drizzle-kit';

      export default defineConfig({
        dialect: 'gel',
      });

.. edb:split-section::

  Now, let's pull the database schema into Drizzle. This step will introspect
  our Gel database and generate TypeScript files that we can use with Drizzle.

  .. code-block:: bash

      $ npx drizzle-kit pull

.. edb:split-section::

  Drizzle Kit generated the schema based on the Gel schema we defined earlier. You can find this file in the ``drizzle`` directory along with the ``relations.ts`` file. The ``relations.ts`` file contains the relationships between the tables in our schema. The schema file that Drizzle generated will look like this:

  .. note::

    You should not modify the reflected schema directly. The correct flow is always: [change :dotgel:`dbschema/default` file] -> [run ``drizzle-kit pull``].


  .. code-block:: typescript
      :caption: drizzle/schema.ts
      :class: collapsible

      import { gelTable, uniqueIndex, uuid, text, timestamptz, smallint, foreignKey } from "drizzle-orm/gel-core"
      import { sql } from "drizzle-orm"


      export const book = gelTable("Book", {
      	id: uuid().default(sql`uuid_generate_v4()`).primaryKey().notNull(),
      	author: text(),
      	genre: text(),
      	readDate: timestamptz("read_date"),
      	title: text().notNull(),
      	year: smallint(),
      }, (table) => [
      	uniqueIndex("5f1d3546-1943-11f0-be08-df1707d45eaa;schemaconstr").using("btree", table.id.asc().nullsLast().op("uuid_ops")),
      ]);

      export const note = gelTable("Note", {
      	id: uuid().default(sql`uuid_generate_v4()`).primaryKey().notNull(),
      	bookId: uuid("book_id").notNull(),
      	createdAt: timestamptz("created_at").default(sql`(clock_timestamp())`),
      	text: text().notNull(),
      }, (table) => [
      	uniqueIndex("5f1e4652-1943-11f0-a4a0-f1f912666606;schemaconstr").using("btree", table.id.asc().nullsLast().op("uuid_ops")),
      	foreignKey({
      		columns: [table.bookId],
      		foreignColumns: [book.id],
      		name: "Note_fk_book"
      	}),
      ]);


.. edb:split-section::

  Finally, we need to update the hooks in our ``gel.toml`` file to ensure that our
  Drizzle schema stays in sync with our Gel schema. Every time we apply a migration,
  we want to run the Drizzle pull command to update the TypeScript files.

  .. code-block:: toml-diff
      :caption: gel.toml

      + [hooks]
      + after_migration_apply = [
      +   "npx drizzle-kit pull"
      + ]


4. Creating the database client
================================

.. edb:split-section::

  Now that we have our schema set up, let's create a database client that we can use
  throughout our application. This client will connect to our Gel database using
  Drizzle.

  .. code-block:: typescript
      :caption: src/db/index.ts

      import { drizzle } from 'drizzle-orm/gel';
      import { createClient } from 'gel';

      import * as schema from '../../drizzle/schema';
      import * as relations from '../../drizzle/relations';

      // Initialize Gel client
      const gelClient = createClient();

      // Create Drizzle instance
      export const db = drizzle({ client: gelClient, schema: {
        ...schema,
        ...relations,
      } });

      // Helper types for use in our application
      export type Book = typeof schema.book.$inferSelect;
      export type NewBook = typeof schema.book.$inferInsert;
      export interface BookWithNotes extends Book {
        notes: Note[];
      };

      export type Note = typeof schema.note.$inferSelect;
      export type NewNote = typeof schema.note.$inferInsert;

5. Implementing API Routes
===========================

Next, let's implement the API routes for our book notes application. With Next.js, we can create API endpoints in the ``app/api`` directory to handle HTTP requests.

.. edb:split-section::

  We'll start by creating a route for managing all books. This will handle
  fetching all books and adding new books. The ``GET`` method will return a list
  of all books, while the ``POST`` method will allow us to add a new book.
  We'll also include error handling for both methods. In both, we'll use
  Drizzle ORM to interact with the database.

  .. code-block:: typescript
      :caption: app/api/books/route.ts

      import { NextResponse } from 'next/server';
      import { db } from '@/src/db';
      import { books } from '@/drizzle/schema';

      export async function GET() {
        try {
          const allBooks = await db.query.book.findMany({
            with: {
              notes: true,
            },
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

      export async function POST(request: Request) {
        try {
          const body = await request.json();

          const result = await db.insert(book).values({
            title: body.title,
            author: body.author,
            year: body.year,
            genre: body.genre,
            readDate: new Date(body.read_date),
          }).returning();

          return NextResponse.json(result[0], { status: 201 });
        } catch (error) {
          console.error('Error adding book:', error);
          return NextResponse.json(
            { error: 'Failed to add book' },
            { status: 500 }
          );
        }
      }

.. edb:split-section::

  Next, let's create a route for managing a specific book by its ID. This will handle
  getting book details, updating books, and deleting books.

  - ``GET`` method will fetch a specific book by its ID.
  - ``PUT`` method will update the book details based on the request body.
  - ``DELETE`` method will delete the book and all its associated notes.

  We'll also include error handling for each method.

  .. code-block:: typescript
      :caption: src/app/api/books/[id]/route.ts

      import { NextResponse } from 'next/server';
      import { db } from '@/src/db';
      import { book, note } from '@/drizzle/schema';
      import { eq } from 'drizzle-orm';

      export async function GET(
        request: Request,
        { params }: { params: Promise<{ id: string }> }
      ) {
        const { id } = await params;
        try {
          const requestedBook = await db.query.book.findFirst({
            where: eq(books.id, id),
            with: {
              note: true,
            },
          });

          if (!requestedBook) {
            return NextResponse.json(
              { error: 'Book not found' },
              { status: 404 }
            );
          }

          return NextResponse.json(requestedBook);
        } catch (error) {
          console.error('Error fetching book:', error);
          return NextResponse.json(
            { error: 'Failed to fetch book' },
            { status: 500 }
          );
        }
      }

      export async function PUT(
        request: Request,
        { params }: { params: Promise<{ id: string }> }
      ) {
        const { id } = await params;
        try {
          const body = await request.json();

          const result = await db.update(book)
            .set({
              title: body.title,
              author: body.author,
              year: body.year,
              genre: body.genre,
              readDate: new Date(body.read_date),
            })
            .where(eq(books.id, id))
            .returning();

          if (result.length === 0) {
            return NextResponse.json(
              { error: 'Book not found' },
              { status: 404 }
            );
          }

          return NextResponse.json(result[0]);
        } catch (error) {
          console.error('Error updating book:', error);
          return NextResponse.json(
            { error: 'Failed to update book' },
            { status: 500 }
          );
        }
      }

      export async function DELETE(
        request: Request,
        { params }: { params: Promise<{ id: string }> }
      ) {
        const { id } = await params;
        try {
          // First delete associated notes
          await db.delete(note).where(eq(note.bookId, id));

          // Then delete the book
          const result = await db.delete(book)
            .where(eq(book.id, id))
            .returning();

          if (result.length === 0) {
            return NextResponse.json(
              { error: 'Book not found' },
              { status: 404 }
            );
          }

          return NextResponse.json({ success: true });
        } catch (error) {
          console.error('Error deleting book:', error);
          return NextResponse.json(
            { error: 'Failed to delete book' },
            { status: 500 }
          );
        }
      }

.. edb:split-section::

  Now, let's create a route for adding notes to a book. This endpoint will handle the
  creation of new notes for a specific book. The ``POST`` method will accept
  a request body with the note text and the book ID.

  .. code-block:: typescript
      :caption: src/app/api/books/[id]/notes/route.ts

      import { NextResponse } from 'next/server';
      import { db } from '@/src/db';
      import { note } from '@/drizzle/schema';

      export async function POST(
        request: Request,
        { params }: { params: Promise<{ id: string }> }
      ) {
        const { id } = await params;
        try {
          const body = await request.json();

          const result = await db.insert(note).values({
            text: body.text,
            bookId: id,
          }).returning();

          return NextResponse.json(result[0], { status: 201 });
        } catch (error) {
          console.error('Error adding note:', error);
          return NextResponse.json(
            { error: 'Failed to add note' },
            { status: 500 }
          );
        }
      }

.. edb:split-section::

  Finally, let's create a route for updating and deleting individual notes.
  This will handle the ``PUT`` and ``DELETE`` methods for a specific note.
  The ``PUT`` method will update the note text, while the ``DELETE`` method
  will delete the note.

  .. code-block:: typescript
      :caption: src/app/api/notes/[id]/route.ts

      import { NextResponse } from 'next/server';
      import { db } from '@/src/db';
      import { note } from '@/drizzle/schema';
      import { eq } from 'drizzle-orm';

      export async function PUT(
        request: Request,
        { params }: { params: Promise<{ id: string }> }
      ) {
        const { id } = await params;
        try {
          const body = await request.json();

          const result = await db.update(note)
            .set({
              text: body.text,
            })
            .where(eq(note.id, id))
            .returning();

          if (result.length === 0) {
            return NextResponse.json(
              { error: 'Note not found' },
              { status: 404 }
            );
          }

          return NextResponse.json(result[0]);
        } catch (error) {
          console.error('Error updating note:', error);
          return NextResponse.json(
            { error: 'Failed to update note' },
            { status: 500 }
          );
        }
      }

      export async function DELETE(
        request: Request,
        { params }: { params: Promise<{ id: string }> }
      ) {
        const { id } = await params;
        try {
          const result = await db.delete(note)
            .where(eq(notes.id, id))
            .returning();

          if (result.length === 0) {
            return NextResponse.json(
              { error: 'Note not found' },
              { status: 404 }
            );
          }

          return NextResponse.json({ success: true });
        } catch (error) {
          console.error('Error deleting note:', error);
          return NextResponse.json(
            { error: 'Failed to delete note' },
            { status: 500 }
          );
        }
      }

.. edb:split-section::

  We can test our API routes using a tool like Postman or cURL. Let's start the
  development server and test the routes.

  .. code-block:: bash

      $ npm run dev

.. edb:split-section::

  You can now access the API routes at ``http://localhost:3000/api`` (or the port specified in your environment). For example, to access the books route, you can go to ``http://localhost:3000/api/books``. You can use Postman or cURL to test the endpoints. For example, to fetch all books, you can use the following cURL command:

  .. code-block:: bash

      $ curl -X GET http://localhost:3000/api/books

.. edb:split-section::

  To add a new book, you can use the following cURL command:

  .. code-block:: bash

      $ curl -X POST http://localhost:3000/api/books \
        -H "Content-Type: application/json" \
        -d '{"title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "year": 1925, "genre": "Fiction", "read_date": "2023-10-01"}'

.. edb:split-section::

  Or to create a new note for a book, you can use the following cURL command
  (replace ``<BOOK_ID>`` with the actual book ID):

  .. code-block:: bash

      $ curl -X POST http://localhost:3000/api/books/<BOOK_ID>/notes \
        -H "Content-Type: application/json" \
        -d '{"text": "This is a great book!"}'

6. Building the UI
==================

Now that we have our API routes in place, we can build a user interface for our book
notes application. We'll use Tailwind CSS for styling, which was included when we
created our Next.js application.

We won't go into extensive UI details, but here's a basic implementation for the
home page that lists all books.

.. edb:split-section::

  We'll start by creating a home page that fetches and displays all books from our API.
  This page will also include a link to add a new book.
  We'll use the ``useEffect`` hook to fetch the books when the component mounts.
  We'll also handle loading states and error handling.
  The home page will display a list of books with their titles, authors, publication years,
  genres, and the number of notes associated with each book.

  .. code-block:: typescript
      :caption: app/page.tsx
      :class: collapsible

      'use client';

      import { useState, useEffect } from 'react';
      import Link from 'next/link';
      import { BookWithNotes } from '@/db';

      export default function Home() {
        const [books, setBooks] = useState<Book[]>([]);
        const [loading, setLoading] = useState(true);

        useEffect(() => {
          async function fetchBooks() {
            try {
              const response = await fetch('/api/books');
              if (!response.ok) throw new Error('Failed to fetch books');
              const data = await response.json();
              setBooks(data);
            } catch (error) {
              console.error('Error:', error);
            } finally {
              setLoading(false);
            }
          }

          fetchBooks();
        }, []);

        if (loading) {
          return (
            <div className="flex justify-center items-center min-h-screen">
              <p className="text-xl">Loading...</p>
            </div>
          );
        }

        return (
          <main className="container max-w-7xl mx-auto px-4 py-10">
            <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-8 text-center">
              My Book Notes
            </h1>

            <Link
              href="/books/add"
              className="bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-400 text-white font-medium px-4 py-2 rounded transition duration-150 ease-in-out mb-8 inline-block"
            >
              Add New Book
            </Link>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mt-6">
              {books.length === 0 ? (
                <p className="text-lg text-center">No books found. Add your first book!</p>
              ) : (
                books.map((book) => (
                  <Link
                    key={book.id}
                    href={`/books/${book.id}`}
                    className="mt-3 inline-block font-medium hover:shadow-lg transform hover:scale-105 transition duration-200"
                  >
                    <div
                      className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg p-6 shadow-md "
                    >
                      <h2 className="text-xl font-semibold mb-2">{book.title}</h2>
                      {book.author && (
                        <p className="text-gray-600 dark:text-gray-400 mb-1">
                          by {book.author}
                        </p>
                      )}
                      {book.year && (
                        <p className="text-sm text-gray-500 dark:text-gray-400">
                          Published: {book.year}
                        </p>
                      )}
                      {book.genre && (
                        <p className="text-sm text-gray-500 dark:text-gray-400">
                          Genre: {book.genre}
                        </p>
                      )}
                      <p className="mt-4 text-sm font-medium text-gray-700 dark:text-gray-300">
                        {book.notes?.length || 0} notes
                      </p>

                    </div>
                  </Link>
                ))
              )}
            </div>
          </main>
        );
      }

.. edb:split-section::

  Next, let's create a form component for adding and editing books. This will be used in
  both the "Add Book" page and the "Edit Book" page.

  .. code-block:: typescript
      :caption: src/components/BookForm.tsx
      :class: collapsible

      'use client';

      import { useState, FormEvent } from 'react';
      import { useRouter } from 'next/navigation';
      import { Book } from '../db';

      interface BookFormProps {
        book?: Book;
        isEditing?: boolean;
      }

      export default function BookForm({ book, isEditing = false }: BookFormProps) {
        const router = useRouter();
        const [title, setTitle] = useState(book?.title || '');
        const [author, setAuthor] = useState(book?.author || '');
        const [year, setYear] = useState(book?.year?.toString() || '');
        const [genre, setGenre] = useState(book?.genre || '');
        const [readDate, setReadDate] = useState(
          book?.readDate
            ? new Date(book.readDate).toISOString().split('T')[0]
            : ''
        );

        const handleSubmit = async (e: FormEvent) => {
          e.preventDefault();

          const bookData = {
            title,
            author,
            year: year ? parseInt(year) : undefined,
            genre,
            read_date: readDate || undefined,
          };

          try {
            if (isEditing && book) {
              // Update existing book
              await fetch(`/api/books/${book.id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(bookData),
              });
            } else {
              // Create new book
              await fetch('/api/books', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(bookData),
              });
            }

            router.push('/');
            router.refresh();
          } catch (error) {
            console.error('Error saving book:', error);
          }
        };

        return (
          <form onSubmit={handleSubmit} className="max-w-md mx-auto bg-gray-900 p-6 rounded-lg shadow">
            <div className="mb-4">
              <label className="block text-white font-semibold mb-1" htmlFor="title">
                Title*
              </label>
              <input
                id="title"
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                required
                className="w-full px-4 py-2 bg-gray-800 text-white border border-gray-700 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 transition duration-150"
              />
            </div>

            <div className="mb-4">
              <label className="block text-white font-semibold mb-1" htmlFor="author">
                Author
              </label>
              <input
                id="author"
                type="text"
                value={author}
                onChange={(e) => setAuthor(e.target.value)}
                className="w-full px-4 py-2 bg-gray-800 text-white border border-gray-700 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 transition duration-150"
              />
            </div>

            <div className="mb-4">
              <label className="block text-white font-semibold mb-1" htmlFor="year">
                Publication Year
              </label>
              <input
                id="year"
                type="number"
                value={year}
                onChange={(e) => setYear(e.target.value)}
                className="w-full px-4 py-2 bg-gray-800 text-white border border-gray-700 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 transition duration-150"
              />
            </div>

            <div className="mb-4">
              <label className="block text-white font-semibold mb-1" htmlFor="genre">
                Genre
              </label>
              <input
                id="genre"
                type="text"
                value={genre}
                onChange={(e) => setGenre(e.target.value)}
                className="w-full px-4 py-2 bg-gray-800 text-white border border-gray-700 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 transition duration-150"
              />
            </div>

            <div className="mb-6">
              <label className="block text-white font-semibold mb-1" htmlFor="readDate">
                Date Read
              </label>
              <input
                id="readDate"
                type="date"
                value={readDate}
                onChange={(e) => setReadDate(e.target.value)}
                className="w-full px-4 py-2 bg-gray-800 text-white border border-gray-700 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 transition duration-150"
              />
            </div>

            <div className="flex justify-between">
              <button
                type="button"
                onClick={() => router.back()}
                className="px-4 py-2 border border-gray-600 text-white rounded hover:bg-gray-700 transition duration-150"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition duration-150"
              >
                {isEditing ? 'Update Book' : 'Add Book'}
              </button>
            </div>
          </form>
        );
      }

.. edb:split-section::

  Now, let's create the "Add Book" page that uses our form component.

  .. code-block:: typescript
      :caption: app/books/add/page.tsx

      'use client';

      import BookForm from "@/src/components/BookForm";

      export default function AddBookPage() {
        return (
          <div className="container mx-auto p-4">
            <h1 className="text-2xl font-bold mb-6">Add New Book</h1>
            <BookForm />
          </div>
        );
      }

.. edb:split-section::

  Let's also create a page to view book details and manage notes.

  .. code-block:: typescript
      :caption: src/app/books/[id]/page.tsx
      :class: collapsible

      'use client';

      import { useState, useEffect, FormEvent, use } from 'react';
      import { useRouter } from 'next/navigation';
      import Link from 'next/link';
      import { BookWithNotes } from '@/src/db';

      export default function BookDetailPage({ params }: { params: Promise<{ id: string }> }) {
        const { id } = use(params);
        const router = useRouter();
        const [book, setBook] = useState<BookWithNotes | null>(null);
        const [loading, setLoading] = useState(true);
        const [noteText, setNoteText] = useState('');

        useEffect(() => {
          async function fetchBook() {
            try {
              const response = await fetch(`/api/books/${id}`);
              if (!response.ok) {
                if (response.status === 404) {
                  router.push('/');
                  return;
                }
                throw new Error('Failed to fetch book');
              }
              const data = await response.json();
              setBook(data);
            } catch (error) {
              console.error('Error:', error);
            } finally {
              setLoading(false);
            }
          }

          fetchBook();
        }, [id, router]);

        const handleAddNote = async (e: FormEvent) => {
          e.preventDefault();

          if (!noteText.trim()) return;

          try {
            const response = await fetch(`/api/books/${id}/notes`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ text: noteText }),
            });

            if (!response.ok) throw new Error('Failed to add note');

            const newNote = await response.json();
            setBook(prev => prev ? {
              ...prev,
              notes: [...prev.notes, newNote]
            } : null);
            setNoteText('');
          } catch (error) {
            console.error('Error adding note:', error);
          }
        };

        const handleDeleteNote = async (noteId: string) => {
          try {
            const response = await fetch(`/api/notes/${noteId}`, {
              method: 'DELETE',
            });

            if (!response.ok) throw new Error('Failed to delete note');

            setBook(prev => prev ? {
              ...prev,
              notes: prev.notes.filter(note => note.id !== noteId)
            } : null);
          } catch (error) {
            console.error('Error deleting note:', error);
          }
        };

        const handleDeleteBook = async () => {
          if (!confirm('Are you sure you want to delete this book and all its notes?')) {
            return;
          }

          try {
            const response = await fetch(`/api/books/${id}`, {
              method: 'DELETE',
            });

            if (!response.ok) throw new Error('Failed to delete book');

            router.push('/');
          } catch (error) {
            console.error('Error deleting book:', error);
          }
        };

        if (loading) {
          return (
            <div className="flex justify-center items-center min-h-screen">
              <p className="text-xl">Loading...</p>
            </div>
          );
        }

        if (!book) {
          return (
            <div className="container mx-auto p-4">
              <p>Book not found.</p>
              <Link href="/" className="text-blue-500 hover:text-blue-600">
                Back to All Books
              </Link>
            </div>
          );
        }

        return (
          <div className="max-w-4xl mx-auto px-4 py-6">
            <div className="mb-6">
              <Link href="/" className="text-blue-400 hover:underline">
                ← Back
              </Link>
            </div>

            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-8">
              <h1 className="text-4xl font-extrabold leading-tight text-white">
                {book.title}
              </h1>
              <div className="mt-4 sm:mt-0 space-x-2">
                <Link
                  href={`/books/${id}/edit`}
                  className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-400 transition duration-150 inline-block"
                >
                  Edit
                </Link>
                <button
                  onClick={handleDeleteBook}
                  className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-400 transition duration-150"
                >
                  Delete
                </button>
              </div>
            </div>

            <div className="bg-gray-800 p-6 rounded-lg mb-8">
              {book.author && (
                <p className="text-lg font-medium mb-2 text-white">
                  by {book.author}
                </p>
              )}
              <div className="space-y-1 text-sm text-gray-300">
                {book.year && <p>Published: {book.year}</p>}
                {book.genre && <p>Genre: {book.genre}</p>}
                {book.readDate && (
                  <p>Read on: {new Date(book.readDate).toLocaleDateString()}</p>
                )}
              </div>
            </div>

            <div className="mb-8">
              <h2 className="text-2xl font-semibold text-white mb-4">Notes</h2>
              <form onSubmit={handleAddNote} className="mb-6">
                <div className="flex">
                  <input
                    type="text"
                    value={noteText}
                    onChange={(e) => setNoteText(e.target.value)}
                    placeholder="Add a new note..."
                    className="flex-grow px-4 py-2 bg-gray-700 text-white placeholder-gray-400 border border-gray-600 rounded-l focus:outline-none focus:ring-2 focus:ring-blue-500 transition duration-150"
                  />
                  <button
                    type="submit"
                    className="px-5 py-2 bg-blue-600 text-white rounded-r hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-400 transition duration-150"
                  >
                    Add
                  </button>
                </div>
              </form>

              {book.notes.length === 0 ? (
                <p className="text-gray-400 italic">
                  No notes yet. Add your first note above.
                </p>
              ) : (
                <ul className="space-y-4">
                  {book.notes.map((note) => (
                    <li
                      key={note.id}
                      className="flex justify-between items-start bg-gray-800 text-white p-4 rounded shadow-sm"
                    >
                      <div>
                        <p>{note.text}</p>
                        {note.createdAt && (
                          <p className="text-xs text-gray-400 mt-1">
                            {new Date(note.createdAt).toLocaleString()}
                          </p>
                        )}
                      </div>
                      <button
                        onClick={() => handleDeleteNote(note.id)}
                        className="text-red-400 hover:text-red-600 focus:outline-none transition duration-150"
                      >
                        Delete
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        );
      }

.. edb:split-section::

  For a complete application, you would also need to implement an edit page for books.
  Here's a simplified example:

  .. code-block:: typescript
      :caption: src/app/books/[id]/edit/page.tsx
      :class: collapsible

      'use client';

      import { useState, useEffect, use } from 'react';
      import { useRouter } from 'next/navigation';
      import { Book } from '@/src/db';
      import BookForm from '@/src/components/BookForm';

      export default function EditBookPage({ params }: { params: Promise<{ id: string }> }) {
        const router = useRouter();
        const { id } = use(params);
        const [book, setBook] = useState<Book | null>(null);
        const [loading, setLoading] = useState(true);

        useEffect(() => {
          async function fetchBook() {
            try {
              const response = await fetch(`/api/books/${id}`);
              if (!response.ok) {
                if (response.status === 404) {
                  router.push('/');
                  return;
                }
                throw new Error('Failed to fetch book');
              }
              const data = await response.json();
              setBook(data);
            } catch (error) {
              console.error('Error:', error);
            } finally {
              setLoading(false);
            }
          }

          fetchBook();
        }, [id, router]);

        if (loading) {
          return (
            <div className="flex justify-center items-center min-h-screen">
              <p className="text-xl">Loading...</p>
            </div>
          );
        }

        if (!book) {
          return (
            <div className="container mx-auto p-4">
              <p>Book not found.</p>
              <button onClick={() => router.push('/')} className="text-blue-500 hover:text-blue-600">
                Back to All Books
              </button>
            </div>
          );
        }

        return (
          <div className="container mx-auto p-4">
            <h1 className="text-2xl font-bold mb-6">Edit Book</h1>
            <BookForm book={book} isEditing={true} />
          </div>
        );
      }

.. edb:split-section::

  These UI components provide a basic but functional user interface for our Book Notes
  application. Tailwind CSS helps us create a clean and responsive design with minimal
  effort.

  Since we're focusing on the Gel and Drizzle integration, we won't detail every UI
  component, but the pattern is consistent throughout the application:

  - We use React hooks for state management (useState, useEffect)
  - We call our API endpoints to fetch and modify data
  - We use Tailwind CSS classes for styling the components
  - We implement client-side navigation with Next.js's useRouter

7. Testing the application
===========================

.. edb:split-section::

  Now that we have built our API routes and basic UI, let's test our application.
  Start the development server:

  .. code-block:: bash

      $ npm run dev

.. edb:split-section::

  Navigate to http://localhost:3000 in your browser, and you should see your Book Notes
  application. Try performing these operations to ensure everything is working correctly:

  1. Adding a new book
  2. Viewing book details
  3. Adding notes to a book
  4. Editing book information
  5. Deleting notes
  6. Deleting a book (which should also delete its notes)

  If you encounter any issues, check your browser's developer console and the terminal
  running your Next.js server for error messages.

8. Next steps
==============

Congratulations! You've built a Book Notes application using Gel, Drizzle, and Next.js.
This tutorial demonstrated how these technologies can work together to create a
full-stack application.

Here are some ideas for extending the application:

1. **Add authentication**: Implement user authentication to allow multiple users
   to have their own book collections.

2. **Advanced filtering**: Add the ability to filter books by genre, author, or
   reading status.

3. **Book statistics**: Create a dashboard with statistics about your reading
   habits.

4. **Reading goals**: Implement a feature to set and track reading goals.

5. **Book recommendations**: Add a feature to recommend books based on what
   you've already read.

6. **Import/Export**: Allow users to import or export their book data.

7. **Search functionality**: Implement full-text search across books and notes.

To further explore the capabilities of Gel and Drizzle, you can check out these resources:

- `Gel Documentation <https://docs.geldata.com/>`_
- `Drizzle ORM Documentation <https://orm.drizzle.team/docs/overview>`_
- `Next.js Documentation <https://nextjs.org/docs>`_

Remember, you can find the complete source code for this tutorial in our
`Gel Examples repository <https://github.com/geldata/gel-examples/tree/main/drizzle-book-notes-app>`_.

Happy coding!
