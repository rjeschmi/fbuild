import io
import pickle
import time

import fbuild.path

# ------------------------------------------------------------------------------

class Backend:
    def __init__(self, ctx):
        self._ctx = ctx

    # --------------------------------------------------------------------------

    def connect(self, *args, **kwargs):
        """Connect to the database."""
        raise NotImplementedError


    def close(self, *args, **kwargs):
        """Connect to the database backend."""
        raise NotImplementedError

    # --------------------------------------------------------------------------

    def prepare(self, fun_name, fun_digest, bound, srcs, dsts):
        """Queries all the information needed to cache a function."""

        # Check if the function changed.
        fun_dirty = self.check_function(fun_name, fun_digest)

        # Check if this is a new call and get the index.
        call_id, old_result = self.find_call(fun_name, bound)

        # Add the source files to the database.
        call_file_digests = self.check_call_files(call_id, fun_name, srcs)

        # Check extra external call files.
        external_dirty, external_srcs, external_dsts, external_digests = \
            self.check_external_files(call_id, fun_name)

        return (
            fun_dirty,
            call_id,
            old_result,
            call_file_digests,
            external_dirty,
            external_srcs,
            external_dsts,
            external_digests)

    def cache(self,
            fun_dirty,
            fun_name,
            fun_digest,
            call_id,
            bound,
            result,
            call_file_digests,
            external_srcs,
            external_dsts,
            external_digests):
        """Saves the function call into the database."""

        # Lock the db since we're updating data structures.
        if fun_dirty:
            self.save_function(fun_name, fun_digest)

        # Get the real call_id to use in the call files.
        call_id = self.save_call(fun_name, call_id, bound, result)

        self.save_call_files(call_id, fun_name, call_file_digests)

        self.save_external_files(
            fun_name,
            call_id,
            external_srcs,
            external_dsts,
            external_digests)

    # --------------------------------------------------------------------------

    def check_function(self, fun_name, fun_digest):
        """Returns whether or not the function is dirty. Returns True or false
        as well as the function's digest."""

        # Make sure we got the right types.
        assert isinstance(fun_name, str)
        assert isinstance(fun_digest, str)

        old_digest = self.find_function(fun_name)

        # Check if the function changed. If it didn't, assume that the function
        # didn't change either (although any sub-functions could have).
        return old_digest is None or fun_digest != old_digest


    def find_function(self, fun_name):
        """Returns the function record or None if it does not exist."""
        raise NotImplementedError


    def save_function(self, fun_id, fun_name, digest):
        """Insert or update the function's digest."""
        raise NotImplementedError


    def delete_function(self, fun_name):
        """Clear the function from the database."""
        raise NotImplementedError

    # --------------------------------------------------------------------------

    def find_call(self, function, bound):
        """Returns the function call index and result or None if it does not
        exist."""
        raise NotImplementedError


    def save_call(self, fun_name, call_id, bound, result):
        """Insert or update the function call."""
        raise NotImplementedError

    # --------------------------------------------------------------------------

    def check_call_files(self, call_id, fun_name, file_names):
        """Returns all of the dirty call files."""

        # Make sure we got the right types.
        assert isinstance(call_id, (type(None), int))
        assert isinstance(fun_name, str)

        digests = []
        for file_name in file_names:
            d, digest = self.check_call_file(call_id, fun_name, file_name)
            if d:
                digests.append((file_name, digest))

        return digests

    def save_call_files(self, call_id, fun_name, digests):
        """Insert or update the call files."""

        # Make sure we got the right types.
        assert isinstance(call_id, int)
        assert isinstance(fun_name, str)

        for src, digest in digests:
            self.save_call_file(call_id, fun_name, src, digest)

    # --------------------------------------------------------------------------

    def check_call_file(self, call_id, fun_name, file_name):
        """Returns if the call file is dirty and the file's digest."""

        # Compute the digest of the file.
        dirty, mtime, digest = self.add_file(file_name)

        # If we don't have a valid call_id, then it's a new call.
        if call_id is None:
            return True, digest

        old_digest = self.find_call_file(call_id, fun_name, file_name)

        # Now, check if the file changed from the previous run. If it did then
        # return True.
        if old_digest is not None and digest == old_digest:
            # We're okay, so return if the file's been updated.
            return dirty, digest
        else:
            # The digest's different, so we're dirty.
            return True, digest


    def find_call_file(self, call_id, fun_name, file_name):
        """Returns the digest of the file from the last time we called this
        function, or None if it does not exist."""
        raise NotImplementedError


    def save_call_file(self, call_id, fun_name, file_name, digest):
        """Insert or update the call file."""
        raise NotImplementedError

    # --------------------------------------------------------------------------

    def check_external_files(self, call_id, fun_name):
        """Returns all of the externally specified call files, and the dirty
        list."""

        # Make sure we got the right types.
        assert isinstance(call_id, (type(None), int))
        assert isinstance(fun_name, str)

        srcs = self.find_external_srcs(call_id, fun_name)
        dsts = self.find_external_dsts(call_id, fun_name)

        external_dirty = False
        digests = []
        for src in srcs:
            try:
                d, digest = self.check_call_file(call_id, fun_name, src)
            except OSError:
                external_dirty = True
            else:
                if d:
                    digests.append((src, digest))

        return external_dirty, srcs, dsts, digests


    def find_external_srcs(self, call_id, fun_name):
        """Returns all of the externally specified call src files"""
        raise NotImplementedError


    def find_external_dsts(self, call_id, fun_name):
        """Returns all of the externally specified call dst files"""
        raise NotImplementedError


    def save_external_files(self, fun_name, call_id, srcs, dsts, digests):
        """Insert or update the externally specified call files."""
        raise NotImplementedError

    # --------------------------------------------------------------------------

    def add_file(self, file_name):
        """Insert or update the file information. Returns True if the content
        of the file is different from what was in the table."""

        # Make sure we got the right types.
        assert isinstance(file_name, str)

        mtime = fbuild.path.Path(file_name).getmtime()

        old_mtime, old_digest = self.find_file(file_name)

        if old_mtime is not None:
            # If the file was modified less than 1.0 seconds ago, recompute the
            # hash since it still could have changed even with the same mtime.
            # If True, then assume the file has not been modified.
            if mtime == old_mtime and time.time() - mtime > 1.0:
                return False, mtime, old_digest

        # The mtime changed, so let's see if the content's changed.
        digest = fbuild.path.Path.digest(file_name)

        if digest == old_digest:
            # Save the new mtime.
            self.save_file(file_name, mtime, digest)
            return False, mtime, digest

        # Since the function changed, all of the calls that used this
        # function are dirty.
        self.delete_file(file_name)

        # Now, add the file back to the database.
        self.save_file(file_name, mtime, digest)

        # Returns True since the file changed.
        return True, mtime, digest


    def find_file(self, file_name):
        """Returns the file's old mtime and digest or None if it does not
        exist."""
        raise NotImplementedError


    def save_file(self, file_name, mtime, digest):
        """Insert or update the file."""
        raise NotImplementedError


    def delete_file(self, file_name):
        """Remove the file from the database."""
        raise NotImplementedError

# ------------------------------------------------------------------------------

class Pickler(pickle.Pickler):
    """Create a custom pickler that won't try to pickle the context."""

    def __init__(self, ctx, *args, **kwargs):
        super().__init__(*args, protocol=pickle.HIGHEST_PROTOCOL, **kwargs)
        self.ctx = ctx

    def persistent_id(self, obj):
        if obj is self.ctx:
            return 'ctx'
        else:
            return None

class Unpickler(pickle.Unpickler):
    """Create a custom unpickler that will substitute the current context."""

    def __init__(self, ctx, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ctx = ctx

    def persistent_load(self, pid):
        if pid == 'ctx':
            return self.ctx
        else:
            raise pickle.UnpicklingError('unsupported persistent object')


def pickle_dumps(ctx, obj):
    f = io.BytesIO()
    pickler = Pickler(ctx, f)
    pickler.dump(obj)

    return f.getvalue()


def pickle_loads(ctx, string):
    f = io.BytesIO(string)
    unpickler = Unpickler(ctx, f)
    return unpickler.load()