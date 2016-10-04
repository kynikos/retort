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

from .exceptions import (ExistingSessionError, UnreadableDatabaseError,
                         UnwritableDatabaseError)


class Session(object):
    def process_request(self, app):
        raise NotImplementedError()


class NullSession(Session):
    def process_request(self, app):
        pass


class TokenJsonSession(Session):
    def __init__(self, db_path, domain, lifespan, path='/', secure=True,
                 httponly=True, cookie_name='RetortSessionID',
                 unidentified_diversion=None, autoextend=False):
        """
        Warning: using JSON files is not recommended in case of high access
        concurrency! Use a more proper database in those cases.
        """
        # For performance, do only what's strictly necessary to configure
        # the object, and leave everything else to process_request, since
        # another session object may be used depending on the matched url,
        # so this would become useless
        super(TokenJsonSession, self).__init__()
        self._dbpath = db_path
        self._cookie_domain = domain
        self._cookie_lifespan = lifespan
        self._cookie_path = path
        self._cookie_secure = secure
        self._cookie_httponly = httponly
        self._cookie_name = cookie_name
        self._unidentified_diversion = unidentified_diversion
        self.autoextend = autoextend

    def process_request(self, app):
        # NullSession is the default, don't always import unneeded modules

        global fcntl
        import fcntl

        global json
        import json

        global uuid
        import uuid

        global datetime, timedelta
        from datetime import datetime, timedelta

        self.app = app
        self._read_data()
        self.id = None
        self.data = None
        self.user = None

        if not self._identify() and self._unidentified_diversion:
            self._unidentified_diversion.serve()

    def _read_data(self, overwrite=True):
        try:
            dbf = open(self._dbpath, 'r')
        # TODO: Specify the exceptions
        except:
            if overwrite:
                self._dbdata = {}
                self._write_data()
                return None
            else:
                raise UnreadableDatabaseError()
        with dbf:
            fcntl.flock(dbf, fcntl.LOCK_EX)
            # Add LOCK_NB to avoid blocking (and raise an exception), but I
            # don't think it's a good idea for this application...
            # fcntl.flock(dbf, fcntl.LOCK_EX | fcntl.LOCK_NB)

            try:
                self._dbdata = json.load(dbf)
            # TODO: Specify the exceptions
            except:
                if overwrite:
                    self._dbdata = {}
                    return None
                else:
                    raise UnreadableDatabaseError()

    def _write_data(self):
        try:
            dbf = open(self._dbpath, 'w')
        # TODO: Specify the exceptions
        except:
            raise UnwritableDatabaseError()
        with dbf:
            fcntl.flock(dbf, fcntl.LOCK_EX)
            # Add LOCK_NB to avoid blocking (and raise an exception), but I
            # don't think it's a good idea for this application...
            # fcntl.flock(dbf, fcntl.LOCK_EX | fcntl.LOCK_NB)

            try:
                json.dump(self._dbdata, dbf)
            # TODO: Specify the exceptions
            except:
                raise UnwritableDatabaseError()

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

        try:
            session_data = self._dbdata['id_to_data'][session_id]
        except KeyError:
            return False

        if self._delete_expired_session(session_id):
            return False

        self.id = session_id
        self.data = session_data
        self.user = session_data['_user']

        if self.autoextend:
            session_data['_expires'] = self._set_cookie(session_id)
            self._write_data()

        return True

    def initiate(self, user, override=False, lifespan=None):
        if self.user:
            if override:
                self.terminate()
            else:
                raise ExistingSessionError()

        session_id = uuid.uuid4()

        expires = self._set_cookie(session_id, lifespan=lifespan)

        session_data = {'_user': user, '_expires': expires}
        self._dbdata['id_to_data'][session_id] = session_data
        self._dbdata['user_to_id'][user] = session_id

        # Check the database for one expired sessions and delete it (prevent
        # memory leaks)
        for session_id in self._dbdata['id_to_data']:
            if self._delete_expired_session(session_id):
                # Deleting one session is enough at preventing memory leaks,
                # since initiate() only adds one more entry
                # This is also extremely important, because otherwise it's not
                # safe to loop on the keys of self._dbdata['id_to_data'] and
                # remove them in the loop itself (I should make a list of them)
                break

        self.id = session_id
        self.data = session_data
        self.user = user

        self._write_data()

    def terminate(self):
        if not self.user:
            return False

        self._delete_session(self, self.id)

        self.id = None
        self.data = None
        self.user = None

        self.app.response.cookies.expire(self._cookie_name)

    def _delete_expired_session(self, session_id):
        expires = self._dbdata['id_to_data'][session_id]['_expires']
        # This compares the expiry date in the session file, not in the cookie,
        # however the date format is exactly the same; also, the date is saved
        # in GMT (i.e. UTC)
        if datetime.strptime(expires, "%a, %d %b %Y %H:%M:%S %Z"
                             ) < datetime.utcnow():
            self._delete_session(session_id)
            return True
        return False

    def _delete_session(self, session_id):
        user = self._dbdata['id_to_data'][session_id]['_user']
        del self._dbdata['id_to_data'][session_id]
        del self._dbdata['user_to_id'][user]
        self._write_data()
