# Retort - Simple Python CGI framework.
# Copyright (C) 2016 Dario Giovannetti <dev@dariogiovannetti.net>
#
# This file is part of Retort.
#
# Retort is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Retort is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Retort.  If not, see <http://www.gnu.org/licenses/>.

# The module must also support Python 2.6
# http://python-future.org/
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
# TODO: Test builtins.super
# from builtins import super


class Cache(object):
    def __init__(self, default_timeout=360):
        # For performance, do only what's strictly necessary to configure
        # the object, and leave everything else to process_request, since
        # another cache object may be used depending on the matched url,
        # so this would become useless
        self._default_timeout = default_timeout

    def set(self, key, value):
        raise NotImplementedError()

    def set_dict(self, key_to_value):
        """
        Ensures the same creation timestamp on all keys.
        """
        raise NotImplementedError()

    def get(self, key, max_age=None, refresh=None):
        raise NotImplementedError()

    def get_dict(self, *keys, **kwargs):
        """
        Useful if the refresh function refreshes multiple keys.

        kwargs = {max_age: None, refresh: None}
        """
        raise NotImplementedError()

    def clear(self, *keys):
        raise NotImplementedError()

    def clear_all(self):
        raise NotImplementedError()


class SQLiteCache(Cache):
    # Use SQLite, not just text files (e.g. JSON) because of concurrency
    # problems!
    def __init__(self, db_path, default_timeout=360):
        # For performance, do only what's strictly necessary to configure
        # the object, and leave everything else to process_request, since
        # another cache object may be used depending on the matched url,
        # so this would become useless
        super(SQLiteCache, self).__init__(default_timeout=default_timeout)

        # Don't always import unneeded modules

        global sqlite3
        import sqlite3

        global datetime, timedelta
        from datetime import datetime, timedelta

        # TODO: Allow explicitly closing the connection, perhaps supporting
        #       the 'with' statement, or adding a 'close' method?
        self._db_conn = sqlite3.connect(db_path)
        # TODO: Investigate why sqlite3.Row doesn't work (doesn't like
        #       row indices to be unicode strings...)
        # self._db_conn.row_factory = sqlite3.Row

        def dict_factory(cursor, row):
            d = {}
            for idx, col in enumerate(cursor.description):
                d[col[0]] = row[idx]
            return d
        self._db_conn.row_factory = dict_factory

    def create_db_table(self):
        cur = self._db_conn.cursor()
        cur.execute('PRAGMA auto_vacuum=FULL')
        cur.execute('''CREATE TABLE Cache (key TEXT PRIMARY KEY,
                                           value TEXT,
                                           creation TEXT NOT NULL)''')
        cur.close()

    def inspect_db_table(self, value=False):
        cur = self._db_conn.cursor()
        fields = ['key', 'creation']
        if value:
            fields.insert(1, 'value')
        cur.execute('''SELECT {0} FROM Cache'''.format(', '.join(fields)))
        text = ['\t'.join(fields)]
        for row in cur:
            text.append('\t'.join(row[field] for field in fields))
        cur.close()
        return '\n'.join(text)

    def set(self, key, value):
        creation = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        cur = self._db_conn.cursor()
        cur.execute('''INSERT OR REPLACE INTO Cache (key, value, creation)
                       VALUES (?, ?, ?)''', (key, value, creation))
        cur.close()
        self._db_conn.commit()

    def set_dict(self, key_to_value):
        creation = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        cur = self._db_conn.cursor()
        for key, value in key_to_value.items():
            cur.execute('''INSERT OR REPLACE INTO Cache (key, value, creation)
                           VALUES (?, ?, ?)''', (key, value, creation))

        cur.close()
        self._db_conn.commit()

    def get(self, key, max_age=None, refresh=None):
        # TODO: In theory there may be a race bug by which a server request
        #       could trigger a duplicate value refresh if it happens *while*
        #       this method is still running due to a previous, but
        #       quasi-simultaneous request; it would be harmless, however, only
        #       inefficient

        maxdelta = timedelta(seconds=self._default_timeout
                             if max_age is None else max_age)

        cur = self._db_conn.cursor()
        cur.execute('''SELECT value, creation FROM Cache
                       WHERE key=?''', (key, ))
        row = cur.fetchone()
        cur.close()

        if row:
            age = (datetime.utcnow() -
                   datetime.strptime(row['creation'], "%Y-%m-%dT%H:%M:%SZ"))
            if age <= maxdelta:
                return row['value']

        # This is reached only if the key doesn't exist or it's expired
        if refresh:
            value = refresh()
            self.set(key, value)
            return value

    def get_dict(self, *keys, **kwargs):
        # TODO: In theory there may be a race bug by which a server request
        #       could trigger a duplicate value refresh if it happens *while*
        #       this method is still running due to a previous, but
        #       quasi-simultaneous request; it would be harmless, however, only
        #       inefficient
        max_age = kwargs.pop('max_age', None)
        refresh = kwargs.pop('refresh', None)

        key_to_value = {}
        maxdelta = timedelta(seconds=self._default_timeout
                             if max_age is None else max_age)
        cur = self._db_conn.cursor()

        for key in keys:
            cur.execute('''SELECT value, creation FROM Cache
                           WHERE key=?''', (key, ))
            row = cur.fetchone()

            if row:
                age = (datetime.utcnow() -
                       datetime.strptime(row['creation'],
                                         "%Y-%m-%dT%H:%M:%SZ"))
                if age <= maxdelta:
                    key_to_value[key] = row['value']
                    continue

            # This is reached only if a key doesn't exist or it's expired
            if refresh:
                key_to_value = refresh()
                self.set_dict(key_to_value)
                break

        cur.close()
        return key_to_value

    def clear(self, *keys):
        cur = self._db_conn.cursor()
        cur.execute('''DELETE FROM Cache WHERE key IN ({0})'''.format(
                    ', '.join('?' * len(keys))), keys)
        cur.close()
        self._db_conn.commit()

    def clear_all(self):
        cur = self._db_conn.cursor()
        cur.execute('''DELETE FROM Cache''')
        cur.close()
        self._db_conn.commit()
