import os

import fbuild
import fbuild.db

# ------------------------------------------------------------------------------

class UnknownPlatform(fbuild.ConfigFailed):
    def __init__(self, platform=None):
        self.platform = platform

    def __str__(self):
        if self.platform is None:
            return 'cannot determine platform'
        else:
            return 'unknown platform: "%s"' % self.platform

# ------------------------------------------------------------------------------

archmap = {
    'irix':      {'posix', 'irix'},
    'irix64':    {'posix', 'irix', 'irix64'},
    'unix':      {'posix'},
    'posix':     {'posix'},
    'linux':     {'posix', 'linux'},
    'gnu/linux': {'posix', 'linux'},
    'solaris':   {'posix', 'solaris'},
    'sunos':     {'posix', 'solaris', 'sunos'},
    'cygwin':    {'posix', 'cygwin'},
    'nocygwin':  {'posix', 'cygwin', 'nocygwin'},
    'mingw':     {'posix', 'mingw'},
    'windows':   {'windows', 'win32'},
    'nt':        {'windows', 'win32', 'nt'},
    'win32':     {'windows', 'win32'},
    'win64':     {'windows', 'win64'},
    'freebsd':   {'posix', 'bsd', 'freebsd'},
    'netbsd':    {'posix', 'bsd', 'netbsd'},
    'openbsd':   {'posix', 'bsd', 'openbsd'},
    'darwin':    {'posix', 'bsd', 'darwin', 'macosx'},
    'osx':       {'posix', 'bsd', 'darwin', 'macosx'},
}

# ------------------------------------------------------------------------------

@fbuild.db.caches
def config(platform=None):
    """L{platform} returns a platform set that describes the various features
    of the specified I{platform}. If I{platform} is I{None}, try to determine
    which platform the system is and return that value. If the platform cannot
    be determined, return I{None}."""
    fbuild.logger.check('determining platform')
    if platform is None:
        try:
            stdout, stderr = fbuild.execute(('uname', '-s'), quieter=1)
        except fbuild.ExecutionError:
            platform = os.name
        else:
            platform = stdout.decode('utf-8').strip().lower()

    try:
        platform = archmap[platform]
    except KeyError:
        fbuild.logger.failed()
        raise UnknownPlatform(platform)
    else:
        fbuild.logger.passed(platform)
        return platform

# ------------------------------------------------------------------------------

def static_obj_suffix(platform=None):
    platform = config(platform)
    if 'windows' in platform:
        return '.obj'
    else:
        return '.o'

def static_lib_prefix(platform=None):
    platform = config(platform)
    if 'windows' in platform:
        return ''
    else:
        return 'lib'

def static_lib_suffix(platform=None):
    platform = config(platform)
    if 'windows' in platform:
        return '.lib'
    else:
        return '.a'

# ------------------------------------------------------------------------------

def shared_obj_suffix(platform=None):
    platform = config(platform)
    if 'windows' in platform:
        return '.obj'
    else:
        return '.os'

def shared_lib_prefix(platform=None):
    platform = config(platform)
    if 'windows' in platform:
        return ''
    else:
        return 'lib'

def shared_lib_suffix(platform=None):
    platform = config(platform)
    if 'windows' in platform:
        return '.lib'
    elif 'darwin' in platform:
        return '.dylib'
    else:
        return '.so'

# ------------------------------------------------------------------------------

def exe_suffix(platform=None):
    platform = config(platform)
    if 'windows' in platform:
        return '.exe'
    else:
        return ''
