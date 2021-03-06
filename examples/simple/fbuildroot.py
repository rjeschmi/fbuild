import pprint

import fbuild
import fbuild.builders.c
import fbuild.config.c as c
import fbuild.config.c.c99 as c99
from fbuild.functools import call
from fbuild.path import Path
from fbuild.record import Record

# -----------------------------------------------------------------------------

def arguments(parser):
    group = parser.add_argument_group('config options')
    group.add_argument('--build-platform')
    group.add_argument('--build-cc')
    group.add_argument('--build-cxx')
    group.add_argument('--host-platform')
    group.add_argument('--host-cc')
    group.add_argument('--host-cxx')
    group.add_argument('--target-platform')
    group.add_argument('--target-cc')
    group.add_argument('--target-cxx')
    group.add_argument('--ocamlc')
    group.add_argument('--ocamlopt')
    group.add_argument('--ocamllex')
    group.add_argument('--ocamlyacc')

# -----------------------------------------------------------------------------

def make_c_builder(ctx, **kwargs):
    return call('fbuild.builders.c.guess', ctx, **kwargs)

def make_cxx_builder(ctx, **kwargs):
    return call('fbuild.builders.cxx.guess', ctx, platform_options=[
            ({'windows'}, {'flags': ['/EHsc']})
        ], **kwargs)

@fbuild.db.caches
def config_build(ctx, *, platform, cc, cxx):
    ctx.logger.log('configuring build phase', color='cyan')

    return Record(
        platform=call('fbuild.builders.platform.guess_platform', ctx, platform),
        c=make_c_builder(ctx, exe=cc),
        cxx=make_cxx_builder(ctx, exe=cxx),
    )

@fbuild.db.caches
def config_host(ctx, build, *,
        platform, cc, cxx, ocamlc, ocamlopt, ocamllex, ocamlyacc):
    ctx.logger.log('configuring host phase', color='cyan')

    platform = call('fbuild.builders.platform.guess_platform', ctx, platform)

    if platform == build.platform:
        ctx.logger.log("using build's c and cxx compiler")
        phase = build
    else:
        phase = Record(
            platform=platform,
            c=make_c_builder(ctx, exe=cc),
            cxx=make_cxx_builder(ctx, exe=cxx))

    phase.ocaml = call('fbuild.builders.ocaml.Ocaml', ctx,
        ocamlc=ocamlc,
        ocamlopt=ocamlopt,
    )
    phase.ocamllex = call('fbuild.builders.ocaml.Ocamllex', ctx, ocamllex)
    phase.ocamlyacc = call('fbuild.builders.ocaml.Ocamlyacc', ctx, ocamlyacc)

    return phase

@fbuild.db.caches
def config_target(ctx, host, *, platform, cc, cxx):
    ctx.logger.log('configuring target phase', color='cyan')

    platform = call('fbuild.builders.platform.guess_platform', ctx, platform)

    if platform == host.platform:
        ctx.logger.log("using host's c and cxx compiler")
        phase = host
    else:
        phase = Record(
            platform=platform,
            c=make_c_builder(ctx, exe=cc),
            cxx=make_cxx_builder(ctx, exe=cxx))

    return phase

# -----------------------------------------------------------------------------

def build(ctx):
    # configure the phases
    build = config_build(ctx,
        platform=ctx.options.build_platform,
        cc=ctx.options.build_cc,
        cxx=ctx.options.build_cxx)

    host = config_host(ctx, build,
        platform=ctx.options.host_platform,
        cc=ctx.options.host_cc,
        cxx=ctx.options.host_cxx,
        ocamlc=ctx.options.ocamlc,
        ocamlopt=ctx.options.ocamlopt,
        ocamllex=ctx.options.ocamllex,
        ocamlyacc=ctx.options.ocamlyacc)

    target = config_target(ctx, host,
        platform=ctx.options.target_platform,
        cc=ctx.options.target_cc,
        cxx=ctx.options.target_cxx)

    types = c99.types(target.c.static)
    stdint_h = c99.stdint_h(target.c.static)

    stdint_types = {'char': types.structural_alias(types.char)}
    for name, field in stdint_h.fields():
        t = getattr(stdint_h, name)
        if isinstance(t, c.IntType):
            stdint_types[field.method.name] = types.structural_alias(t)

    pprint.pprint(stdint_types)

    for lang in 'c', 'cxx':
        for mode in 'static', 'shared':
            builder = target[lang][mode]

            d = Path(lang, mode)

            obj = builder.compile(d / 'bar.c')
            lib = builder.link_lib(d / 'bar', [obj])

            obj = builder.compile(d / 'foo.c')
            exe = builder.link_exe(d / 'foo', [obj], libs=[lib])

            # Linux and Darwin needs the shared library path set in order to
            # properly run.
            if 'linux' in target.platform:
                env = {'LD_LIBRARY_PATH': lib.parent}
            elif 'darwin' in target.platform:
                env = {'DYLD_LIBRARY_PATH': lib.parent}
            else:
                env = None

            ctx.execute([exe], 'running', exe, env=env)
