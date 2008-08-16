from functools import partial

import fbuild.builders
from ...c import MissingHeader
from ...c import gcc

# -----------------------------------------------------------------------------

def config_gxx(env, exe=None, default_exes=['g++', 'c++']):
    try:
        return env.gxx
    except AttributeError:
        pass

    exe = exe or fbuild.builders.find_program(default_exes)

    if not exe:
        raise ConfigFailed('cannot find g++')

    gxx = env['gxx'] = gcc.Gcc(exe)

    if not gxx.check_flags([]):
        raise ConfigFailed('g++ failed to compile an exe')

    return gxx

def make_compiler(*args, make_gcc=config_gxx, **kwargs):
    return gcc.make_compiler(make_gcc=make_gcc, *args, **kwargs)

def make_linker(*args, make_gcc=config_gxx, **kwargs):
    return gcc.make_linker(make_gcc=make_gcc, *args, **kwargs)

# -----------------------------------------------------------------------------

def config_static(env, *args,
        make_compiler=make_compiler,
        make_linker=make_linker,
        compile_flags=['-c'],
        src_suffix='.cc',
        **kwargs):
    from ... import ar

    env.setdefault('cxx', {})['static'] = gcc.make_static(env,
        partial(make_compiler, flags=compile_flags),
        ar.config,
        make_linker,
        src_suffix=src_suffix,
        *args, **kwargs)

def config_shared(env, *args,
        make_compiler=make_compiler,
        make_linker=make_linker,
        compile_flags=['-c', '-fPIC'],
        lib_link_flags=['-shared'],
        src_suffix='.cc',
        **kwargs):
    env.setdefault('cxx', {})['shared'] = gcc.make_shared(env,
        partial(make_compiler, flags=compile_flags),
        partial(make_linker, flags=lib_link_flags),
        make_linker,
        src_suffix=src_suffix,
        *args, **kwargs)

def config(env, exe=None, *args,
        config_gxx=config_gxx,
        config_static=config_static,
        config_shared=config_shared,
        **kwargs):
    config_gxx(env, exe)
    config_static(env, *args, **kwargs)
    config_shared(env, *args, **kwargs)

    return env['cxx']

# -----------------------------------------------------------------------------

def config_ext_hash_map(env):
    if not env['static'].check_header_exists('ext/hash_map'):
        raise MissingHeader('ext/hash_map')

    gxx = env.setdefault('gxx', {})
    gxx['hash_map'] = env['static'].check_compile('''
        #include <ext/hash_map>
        using namespace __gnu_cxx;

        int main(int argc,char** argv) {
            return 0;
        }
    ''', 'checking if gnu hash_map is supported')

def config_extensions(env):
    config_ext_hash_map(env)
