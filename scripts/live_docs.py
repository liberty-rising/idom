import os

from sphinx_autobuild.cli import (
    Server,
    _get_build_args,
    _get_ignore_handler,
    find_free_port,
    get_builder,
    get_parser,
)

from docs.app import IDOM_MODEL_SERVER_URL_PREFIX, make_app, make_examples_component
from idom.server.sanic import PerClientStateServer
from idom.testing import clear_idom_web_modules_dir


# these environment variable are used in custom Sphinx extensions
os.environ["IDOM_DOC_EXAMPLE_SERVER_HOST"] = "127.0.0.1:5555"
os.environ["IDOM_DOC_STATIC_SERVER_HOST"] = ""

_running_idom_servers = []


def wrap_builder(old_builder):
    # This is the bit that we're injecting to get the example components to reload too
    def new_builder():
        [s.stop() for s in _running_idom_servers]
        clear_idom_web_modules_dir()

        server = PerClientStateServer(
            make_examples_component(),
            {"cors": True, "url_prefix": IDOM_MODEL_SERVER_URL_PREFIX},
            make_app(),
        )
        server.run_in_thread("127.0.0.1", 5555, debug=True)
        _running_idom_servers.append(server)
        server.wait_until_started()

        old_builder()

    return new_builder


def main():
    # Mostly copied from https://github.com/executablebooks/sphinx-autobuild/blob/b54fb08afc5112bfcda1d844a700c5a20cd6ba5e/src/sphinx_autobuild/cli.py
    parser = get_parser()
    args = parser.parse_args()

    srcdir = os.path.realpath(args.sourcedir)
    outdir = os.path.realpath(args.outdir)
    if not os.path.exists(outdir):
        os.makedirs(outdir)

    server = Server()

    build_args, pre_build_commands = _get_build_args(args)
    builder = wrap_builder(
        get_builder(server.watcher, build_args, pre_build_commands=pre_build_commands)
    )

    ignore_handler = _get_ignore_handler(args)
    server.watch(srcdir, builder, ignore=ignore_handler)
    for dirpath in args.additional_watched_dirs:
        dirpath = os.path.realpath(dirpath)
        server.watch(dirpath, builder, ignore=ignore_handler)
    server.watch(outdir, ignore=ignore_handler)

    if not args.no_initial_build:
        builder()

    # Find the free port
    portn = args.port or find_free_port()
    if args.openbrowser is True:
        server.serve(port=portn, host=args.host, root=outdir, open_url_delay=args.delay)
    else:
        server.serve(port=portn, host=args.host, root=outdir)


if __name__ == "__main__":
    main()
