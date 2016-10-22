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

from .exceptions import ExistingSessionError


class Session(object):
    def process_request(self, app):
        raise NotImplementedError()


class NullSession(Session):
    def process_request(self, app):
        pass


class TokenSQLiteSession(Session):
    # Use SQLite, not just a text file (e.g. JSON) because of concurrency
    # problems!
    def __init__(self, db_path, domain, lifespan, path='/', secure=True,
                 httponly=True, cookie_name='RetortSessionID',
                 unidentified_diversion=None, autoextend=False):
        # For performance, do only what's strictly necessary to configure
        # the object, and leave everything else to process_request, since
        # another session object may be used depending on the matched url,
        # so this would become useless
        super(TokenSQLiteSession, self).__init__()
        self._db_path = db_path
        self._cookie_domain = domain
        self._cookie_lifespan = lifespan
        self._cookie_path = path
        self._cookie_secure = secure
        self._cookie_httponly = httponly
        self._cookie_name = cookie_name
        self._unidentified_diversion = unidentified_diversion
        self.autoextend = autoextend

    def init_database(self):
        conn = sqlite3.connect(self._db_path)
        cur = conn.cursor()
        cur.execute('''CREATE TABLE Sessions (id INTEGER PRIMARY KEY,
                                              expires TEXT NOT NULL,
                                              user TEXT NOT NULL,
                                              data TEXT)''')
        cur.close()
        conn.close()

    def process_request(self, app):
        # NullSession is the default, don't always import unneeded modules

        global sqlite3
        import sqlite3

        global uuid
        import uuid

        global datetime, timedelta
        from datetime import datetime, timedelta

        self.app = app

        self._db_conn = sqlite3.connect(self._db_path)
        # TODO: Investigate why sqlite3.Row doesn't work (doesn't like
        #       row indices to be unicode strings...)
        # self._db_conn.row_factory = sqlite3.Row

        def dict_factory(cursor, row):
            d = {}
            for idx, col in enumerate(cursor.description):
                d[col[0]] = row[idx]
            return d
        self._db_conn.row_factory = dict_factory

        self.id = None
        self.expires = None
        self.user = None
        self.data = None

        if not self._identify() and self._unidentified_diversion:
            self._unidentified_diversion.serve()

    def _set_cookie(self, session_id, lifespan=None):
        return self.app.response.cookies.add(
                    self._cookie_name, session_id,
                    domain=self._cookie_domain,
                    path=self._cookie_path,
                    lifespan=lifespan or self._cookie_lifespan,
                    secure=self._cookie_secure,
                    httponly=self._cookie_httponly)

    def _identify(self):
        try:
            session_id = self.app.request.cookies[self._cookie_name]
        except KeyError:
            return False

        cur = self._db_conn.execute('''SELECT expires, user, data FROM Sessions
                                    WHERE id=? LIMIT 1''', (session_id, ))
        row = cur.fetchone()
        if not row:
            return False

        if self._delete_expired_session(session_id, row['expires']):
            return False

        self.id = session_id
        self.expires = row['expires']
        self.user = row['user']
        self.data = row['data']

        if self.autoextend:
            self._db_conn.execute('''UPDATE Sessions SET expires=?
                                  WHERE id=?''',
                                  (self._set_cookie(session_id), session_id))
            self._db_conn.commit()

        return True

    def initiate(self, user, override=False, lifespan=None):
        if self.user:
            if override:
                self.terminate()
            else:
                raise ExistingSessionError()

        session_id = uuid.uuid4()

        expires = self._set_cookie(session_id, lifespan=lifespan)
        data = None

        self._db_conn.execute('''INSERT INTO Sessions (id, expires, user, data)
                              VALUES (?, ?, ?, ?)''',
                              (session_id, expires, user, data))

        # Check the database for one expired sessions and delete it (prevent
        # memory leaks)
        cur = self._db_conn.execute('SELECT id, expires FROM Sessions')
        for row in cur:
            if self._delete_expired_session(row['id'], row['expires']):
                # Deleting one session is enough at preventing memory leaks,
                # since initiate() only adds one more entry
                # This is also extremely important, because otherwise it's not
                # safe to loop on the keys of self._dbdata['id_to_data'] and
                # remove them in the loop itself (I should make a list of them)
                break

        self.id = session_id
        self.expires = expires
        self.user = user
        self.data = data

        self._db_conn.commit()

    def terminate(self):
        if not self.user:
            return False

        self._delete_session(self, self.id)

        self.id = None
        self.expires = None
        self.user = None
        self.data = None

        self.app.response.cookies.expire(self._cookie_name)

    def _delete_expired_session(self, session_id, expires):
        # This compares the expiry date in the session file, not in the cookie,
        # however the date format is exactly the same; also, the date is saved
        # in GMT (i.e. UTC)
        if datetime.strptime(expires, "%a, %d %b %Y %H:%M:%S %Z"
                             ) < datetime.utcnow():
            self._delete_session(session_id)
            return True
        return False

    def _delete_session(self, session_id):
        self._db_conn.execute('DELETE FROM Sessions WHERE id=?',
                              (session_id, ))
        self._db_conn.commit()
