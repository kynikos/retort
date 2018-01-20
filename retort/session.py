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
    def __init__(self, db_path, domain, lifetime, path='/', secure=True,
                 httponly=True, cookie_name='RetortSessionID',
                 session_cookie=True, unidentified_diversion=None,
                 autoextend=False):
        # For performance, do only what's strictly necessary to configure
        # the object, and leave everything else to process_request, since
        # another session object may be used depending on the matched url,
        # so this would become useless
        super(TokenSQLiteSession, self).__init__()
        self._db_path = db_path
        # Note how lifetime refers only to the expiry of the session on the
        # server; the cookie may or may not correspond, also because it may
        # be a session cookie, which doesn't have an expires value; on the
        # server, though, every session must always have an expiry date
        self._lifetime = lifetime
        self._cookie_domain = domain
        self._cookie_path = path
        self._cookie_secure = secure
        self._cookie_httponly = httponly
        self._cookie_name = cookie_name
        self._session_cookie = session_cookie
        self._unidentified_diversion = unidentified_diversion
        self.autoextend = autoextend

    def create_db_table(self):
        conn = sqlite3.connect(self._db_path)
        cur = conn.cursor()

        cur.execute('PRAGMA auto_vacuum=FULL')

        # TODO: For some reason using INTEGER for 'id' results in violations
        #       of the primary key uniqueness (see comment when creating
        #       the uuid further below)...
        cur.execute('''CREATE TABLE Sessions (id TEXT PRIMARY KEY,
                                              expiry TEXT NOT NULL,
                                              user TEXT NOT NULL,
                                              data TEXT)''')
        cur.close()
        conn.close()

    def inspect_db_table(self, data=False):
        conn = sqlite3.connect(self._db_path)
        cur = conn.cursor()
        fields = ['id', 'expiry', 'user']
        if data:
            fields.append('data')
        cur.execute('''SELECT {0} FROM Sessions'''.format(', '.join(fields)))
        text = ['\t'.join(fields)]
        for row in cur:
            text.append('\t'.join(str(val) for val in row))
        cur.close()
        conn.close()
        return '\n'.join(text)

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
        # self.expiry is when the session expires on the *server*
        self.expiry = None
        self.user = None
        self.data = None

        if not self._identify() and self._unidentified_diversion:
            self._unidentified_diversion.serve(app)

    def _set_cookie(self, session_id, expires=None):
        self.app.response.cookies.add(
                    self._cookie_name, session_id,
                    domain=self._cookie_domain,
                    path=self._cookie_path,
                    expires=expires,
                    secure=self._cookie_secure,
                    httponly=self._cookie_httponly)

    def _parse_expiry(self, expirystr):
        return datetime.strptime(expirystr, "%Y-%m-%dT%H:%M:%SZ")

    def _format_expiry(self, expiry):
            return expiry.strftime("%Y-%m-%dT%H:%M:%SZ")

    def _identify(self):
        try:
            session_id = self.app.request.cookies[self._cookie_name].value
        except KeyError:
            return False

        cur = self._db_conn.execute('''SELECT expiry, user, data FROM Sessions
                                    WHERE id=? LIMIT 1''', (session_id, ))
        row = cur.fetchone()
        if not row:
            return False

        expiry = self._parse_expiry(row['expiry'])

        if self._delete_expired_session(session_id, expiry):
            return False

        if self.autoextend:
            expiry = datetime.utcnow() + timedelta(seconds=self._lifetime)
            self._db_conn.execute('''UPDATE Sessions SET expiry=?
                                  WHERE id=?''',
                                  (self._format_expiry(expiry), session_id))
            self._db_conn.commit()

            if not self._session_cookie:
                self._set_cookie(session_id, expires=expiry)

        self.id = session_id
        # self.expiry is when the session expires on the *server*
        self.expiry = expiry
        self.user = row['user']
        self.data = row['data']

        return True

    def initiate(self, user, override=False):
        if self.user:
            if override:
                self.terminate()
            else:
                raise ExistingSessionError()

        # TODO: For some reason using integers results in a violation of the
        #       primary key uniqueness...
        # session_id = uuid.uuid4().int
        session_id = uuid.uuid4().hex

        # TODO: Currently data is unused
        data = None

        self.id = session_id
        # self.expiry is when the session expires on the *server*
        self.expiry = datetime.utcnow() + timedelta(seconds=self._lifetime)
        self.user = user
        self.data = data

        self._db_conn.execute('''INSERT INTO Sessions (id, expiry, user, data)
                              VALUES (?, ?, ?, ?)''',
                              (session_id, self._format_expiry(self.expiry),
                               user, data))
        self._db_conn.commit()

        self._set_cookie(session_id,
                         expires=None if self._session_cookie else self.expiry)

        # Check the database for one expired sessions and delete it (prevent
        # memory leaks)
        cur = self._db_conn.execute('SELECT id, expiry FROM Sessions')
        for row in cur:
            if self._delete_expired_session(
                                row['id'], self._parse_expiry(row['expiry'])):
                # Deleting one session is enough at preventing memory leaks,
                # since initiate() only adds one more entry
                # Breaking is also extremely important, because otherwise it's
                # not safe to loop on the keys of self._dbdata['id_to_data']
                # and remove them in the loop itself (I should make a list of
                # them)
                break

    def terminate(self):
        if not self.user:
            return False

        self._delete_session(self.id)

        self.id = None
        # self.expiry is when the session expires on the *server*
        self.expiry = None
        self.user = None
        self.data = None

        try:
            self.app.response.cookies.expire(self._cookie_name)
        except KeyError:
            # If self._session_cookie is True, the response cookie may have not
            # been set for this response
            pass

    def _delete_expired_session(self, session_id, expiry):
        # Note that even though this is an object's method, it doesn't
        # necessarily act on the object's session: it uses self only to reach
        # the database connection
        # This compares the expiry date in the session file, not in the cookie,
        # however the date format is exactly the same; also, the date is saved
        # in GMT (i.e. UTC)
        if expiry < datetime.utcnow():
            self._delete_session(session_id)
            return True
        return False

    def _delete_session(self, session_id):
        # Note that even though this is an object's method, it doesn't
        # necessarily act on the object's session: it uses self only to reach
        # the database connection
        self._db_conn.execute('DELETE FROM Sessions WHERE id=?',
                              (session_id, ))
        self._db_conn.commit()
