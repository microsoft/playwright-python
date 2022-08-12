# PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2
# --------------------------------------------
#
# 1. This LICENSE AGREEMENT is between the Python Software Foundation
# ("PSF"), and the Individual or Organization ("Licensee") accessing and
# otherwise using this software ("Python") in source or binary form and
# its associated documentation.
#
# 2. Subject to the terms and conditions of this License Agreement, PSF hereby
# grants Licensee a nonexclusive, royalty-free, world-wide license to reproduce,
# analyze, test, perform and/or display publicly, prepare derivative works,
# distribute, and otherwise use Python alone or in any derivative version,
# provided, however, that PSF's License Agreement and PSF's notice of copyright,
# i.e., "Copyright (c) 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010,
# 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020 Python Software Foundation;
# All Rights Reserved" are retained in Python alone or in any derivative version
# prepared by Licensee.
#
# 3. In the event Licensee prepares a derivative work that is based on
# or incorporates Python or any part thereof, and wants to make
# the derivative work available to others as provided herein, then
# Licensee hereby agrees to include in any such work a brief summary of
# the changes made to Python.
#
# 4. PSF is making Python available to Licensee on an "AS IS"
# basis.  PSF MAKES NO REPRESENTATIONS OR WARRANTIES, EXPRESS OR
# IMPLIED.  BY WAY OF EXAMPLE, BUT NOT LIMITATION, PSF MAKES NO AND
# DISCLAIMS ANY REPRESENTATION OR WARRANTY OF MERCHANTABILITY OR FITNESS
# FOR ANY PARTICULAR PURPOSE OR THAT THE USE OF PYTHON WILL NOT
# INFRINGE ANY THIRD PARTY RIGHTS.
#
# 5. PSF SHALL NOT BE LIABLE TO LICENSEE OR ANY OTHER USERS OF PYTHON
# FOR ANY INCIDENTAL, SPECIAL, OR CONSEQUENTIAL DAMAGES OR LOSS AS
# A RESULT OF MODIFYING, DISTRIBUTING, OR OTHERWISE USING PYTHON,
# OR ANY DERIVATIVE THEREOF, EVEN IF ADVISED OF THE POSSIBILITY THEREOF.
#
# 6. This License Agreement will automatically terminate upon a material
# breach of its terms and conditions.
#
# 7. Nothing in this License Agreement shall be deemed to create any
# relationship of agency, partnership, or joint venture between PSF and
# Licensee.  This License Agreement does not grant permission to use PSF
# trademarks or trade name in a trademark sense to endorse or promote
# products or services of Licensee, or any third party.
#
# 8. By copying, installing or otherwise using Python, Licensee
# agrees to be bound by the terms and conditions of this License
# Agreement.
#
# type: ignore

import itertools
import os
import threading
import warnings
from asyncio import AbstractChildWatcher, events
from asyncio.log import logger


class ThreadedChildWatcher(AbstractChildWatcher):
    """Threaded child watcher implementation.
    The watcher uses a thread per process
    for waiting for the process finish.
    It doesn't require subscription on POSIX signal
    but a thread creation is not free.
    The watcher has O(1) complexity, its performance doesn't depend
    on amount of spawn processes.
    """

    def __init__(self):
        self._pid_counter = itertools.count(0)
        self._threads = {}

    def is_active(self):
        return True

    def close(self):
        self._join_threads()

    def _join_threads(self):
        """Internal: Join all non-daemon threads"""
        threads = [
            thread
            for thread in list(self._threads.values())
            if thread.is_alive() and not thread.daemon
        ]
        for thread in threads:
            thread.join()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def __del__(self, _warn=warnings.warn):
        threads = [
            thread for thread in list(self._threads.values()) if thread.is_alive()
        ]
        if threads:
            _warn(
                f"{self.__class__} has registered but not finished child processes",
                ResourceWarning,
                source=self,
            )

    def add_child_handler(self, pid, callback, *args):
        loop = events.get_running_loop()
        thread = threading.Thread(
            target=self._do_waitpid,
            name=f"waitpid-{next(self._pid_counter)}",
            args=(loop, pid, callback, args),
            daemon=True,
        )
        self._threads[pid] = thread
        thread.start()

    def remove_child_handler(self, pid):
        # asyncio never calls remove_child_handler() !!!
        # The method is no-op but is implemented because
        # abstract base classes requires it
        return True

    def attach_loop(self, loop):
        pass

    def _do_waitpid(self, loop, expected_pid, callback, args):
        assert expected_pid > 0

        try:
            pid, status = os.waitpid(expected_pid, 0)
        except ChildProcessError:
            # The child process is already reaped
            # (may happen if waitpid() is called elsewhere).
            pid = expected_pid
            returncode = 255
            logger.warning(
                "Unknown child process pid %d, will report returncode 255", pid
            )
        else:
            returncode = _compute_returncode(status)
            if loop.get_debug():
                logger.debug(
                    "process %s exited with returncode %s", expected_pid, returncode
                )

        if loop.is_closed():
            logger.warning("Loop %r that handles pid %r is closed", loop, pid)
        else:
            loop.call_soon_threadsafe(callback, pid, returncode, *args)

        self._threads.pop(expected_pid)


def _compute_returncode(status):
    if os.WIFSIGNALED(status):
        # The child process died because of a signal.
        return -os.WTERMSIG(status)
    elif os.WIFEXITED(status):
        # The child process exited (e.g sys.exit()).
        return os.WEXITSTATUS(status)
    else:
        # The child exited, but we don't understand its status.
        # This shouldn't happen, but if it does, let's just
        # return that status; perhaps that helps debug it.
        return status
