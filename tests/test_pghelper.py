from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from wizzat.testutil import *
from wizzat import pghelper
import psycopg2, psycopg2.extras

class PgHelperTest(TestCase):
    db_info = {
        'host'           : 'localhost',
        'port'           : 5432,
        'user'           : 'wizzat',
        'password'       : 'wizzat',
        'database'       : 'wizzat_testdb',
        'cursor_factory' : psycopg2.extras.DictCursor,
    }

    def test_connection(self):
        with psycopg2.connect(**self.db_info) as conn:
            pass

    def test_execute(self):
        with psycopg2.connect(**self.db_info) as conn:
            conn.autocommit = False
            results = [ x for x in pghelper.iter_results(conn, "SELECT 1 AS foobar") ]
            self.assertEqual(results[0]['foobar'], 1)
            self.assertEqual(results[0][0], 1)

    def test_iteration(self):
        with psycopg2.connect(**self.db_info) as conn:
            conn.autocommit = 0
            result = pghelper.iter_results(conn, """
                SELECT 1 AS foobar
                UNION ALL
                SELECT 2 AS foobar
                UNION ALL
                SELECT 3 AS foobar
                UNION ALL
                SELECT 4 AS foobar
            """)

            self.assertEqual(next(result)["foobar"], 1)
            self.assertEqual(next(result)["foobar"], 2)
            self.assertEqual(next(result)["foobar"], 3)
            self.assertEqual(next(result)["foobar"], 4)

    def test_fetch_results(self):
        with psycopg2.connect(**self.db_info) as conn:
            conn.autocommit = False
            result1 = pghelper.fetch_results(conn, """
                SELECT 1 AS foobar
                UNION ALL
                SELECT 2 AS foobar
                UNION ALL
                SELECT 3 AS foobar
                UNION ALL
                SELECT 4 AS foobar
            """)

            result2 = pghelper.fetch_results(conn, """
                SELECT 2 AS foobar
                UNION ALL
                SELECT 4 AS foobar
                UNION ALL
                SELECT 6 AS foobar
                UNION ALL
                SELECT 8 AS foobar
            """)

            # We would expect accessing result1 to fail if it isn't cached.
            self.assertEqual([ x["foobar"] for x in result1 ], [ 1, 2, 3, 4 ])
            self.assertEqual([ x["foobar"] for x in result2 ], [ 2, 4, 6, 8 ])

    def test_table_exists(self):
        with psycopg2.connect(**self.db_info) as conn:
            conn.autocommit = False
            pghelper.execute(conn, "DROP TABLE IF EXISTS foobar")
            self.assertEqual(pghelper.table_exists(conn, "foobar"), False);
            conn.commit()


            cur = pghelper.execute(conn, "CREATE TABLE foobar (a INTEGER UNIQUE)")
            conn.commit()
            self.assertEqual(pghelper.table_exists(conn, "foobar"), True);

    def test_sequences(self):
        with psycopg2.connect(**self.db_info) as conn:
            conn.autocommit = False
            try:
                pghelper.execute(conn, "drop sequence test_sequence") # if exists isn't supported
            except psycopg2.ProgrammingError:
                conn.rollback()

            pghelper.execute(conn, "create sequence test_sequence")

            self.assertEqual(pghelper.nextval(conn, 'test_sequence'), 1)
            self.assertEqual(pghelper.nextval(conn, 'test_sequence'), 2)
            self.assertEqual(pghelper.nextval(conn, 'test_sequence'), 3)
            self.assertEqual(pghelper.currval(conn, 'test_sequence'), 3)

    def test_currval_limitation(self):
        with psycopg2.connect(**self.db_info) as conn:
            conn.autocommit = False
            try:
                pghelper.execute(conn, "drop sequence test_sequence") # if exists isn't supported
            except psycopg2.ProgrammingError:
                conn.rollback()

            pghelper.execute(conn, "create sequence test_sequence")
            self.assertRaises(psycopg2.OperationalError, lambda: pghelper.currval(conn, 'test_sequence'))

    def test_where_clause(self):
        clause = pghelper.sql_where_from_params(
            foo = True,
            bar = [ 1,2,3 ],
            sam = None,
        )

        self.assertEqual(clause, 'true and bar in (%(bar)s) and foo = %(foo)s and sam is null')

    def test_where_clause__empty_list(self):
        clause = pghelper.sql_where_from_params(
            foo = True,
            bar = [ ],
        )

        self.assertEqual(clause, 'true = false')
