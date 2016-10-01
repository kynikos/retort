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
    def __init__(self, db_path, max_age, cookie_name='RetortSessionID'):
        # For performance, do only what's strictly necessary to configure
        # the object, and leave everything else to process_request, since
        # another session object may be used depending on the matched url,
        # so this would become useless
        super(TokenJsonSession, self).__init__()
        self._dbpath = db_path
        self._max_age = max_age
        self._cookie_name = cookie_name

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
        self.expiry = None

        self.identify()
        # TODO: Execute default action if not authenticated
        # TODO: Optionally renew the session id and/or expiry date

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
            # Add LOCK_NB to avoid blocking, but I don't think it's a good idea
            # for this application...
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
            # Add LOCK_NB to avoid blocking, but I don't think it's a good idea
            # for this application...
            # fcntl.flock(dbf, fcntl.LOCK_EX | fcntl.LOCK_NB)

            try:
                json.dump(self._dbdata, dbf)
            # TODO: Specify the exceptions
            except:
                raise UnwritableDatabaseError()

    def identify(self):
        # TODO: Set proper response headers
        try:
            session_id = self.app.request.cookies[self._cookie_name]
        except KeyError:
            return False

        try:
            session_data = self._dbdata['id_to_data'][session_id]
        except KeyError:
            return False

        if datetime.strptime(session_data['_expiry'],
                             '%Y-%m-%dT%H:%M:%S') < datetime.now():
            return False

        self.id = session_id
        self.data = session_data
        self.user = session_data['_user']
        self.expiry = session_data['_expiry']

    def initiate(self, user, override=False, max_age=None):
        # TODO: Set proper response headers
        if self.user:
            if override:
                self.terminate()
            else:
                raise ExistingSessionError()

        session_id = uuid.uuid4()
        expiry = datetime.now() + timedelta(seconds=max_age or self._max_age)
        session_data = {'_user': user, '_expiry': expiry.strftime(
                                                        '%Y-%m-%dT%H:%M:%S')}
        self._dbdata['id_to_data'][session_id] = session_data
        self._dbdata['user_to_id'][user] = session_id

        # TODO: This may be a good place to optionally check the database for
        #       any expired sessions and clean them up; to optimize
        #       performance, the loop could break at the first removed entry:
        #       since this method is adding only one more entry, this system
        #       would be effective at preventing memory leaks

        self.id = session_id
        self.data = session_data
        self.user = user
        self.expiry = session_data['_expiry']

        self._write_data()

    def terminate(self):
        # TODO: Unset response headers
        if not self.user:
            return False

        del self._dbdata['id_to_data'][self.id]
        del self._dbdata['user_to_id'][self.user]
        self.id = None
        self.data = None
        self.user = None
        self.expiry = None

        self._write_data()
