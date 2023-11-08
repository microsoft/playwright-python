import sys
import playwright
import os
import pathlib
import re
import asyncio

from patch_check import main as patch_check_main


def patch_driver(path: str):
    # patch driver
    print(f'[PATCH] patching driver for "{path}"', file=sys.stderr)

    def replace(path: str, old_str: str, new_str: str):
        with open(path, "r") as f:
            content = f.read()
            content = content.replace(old_str, new_str)
        with open(path, "w") as f:
            f.write(content)

    server_path = path + "/package/lib/server"
    chromium_path = server_path + "/chromium"

    # comment out all "Runtime.enable" occurences
    cr_devtools_path = chromium_path + "/crDevTools.js"
    replace(cr_devtools_path, "session.send('Runtime.enable')", "/*session.send('Runtime.enable'), */")

    cr_page_path = chromium_path + "/crPage.js"
    with open(cr_page_path, "r") as f:
        cr_page = f.read()
        cr_page = cr_page.replace("this._client.send('Runtime.enable', {}),",
                                  "/*this._client.send('Runtime.enable', {}),*/")
        cr_page = cr_page.replace("session._sendMayFail('Runtime.enable');",
                                  "/*session._sendMayFail('Runtime.enable');*/")
    with open(cr_page_path, "w") as f:
        f.write(cr_page)

    cr_sv_worker_path = chromium_path + "/crServiceWorker.js"
    replace(cr_sv_worker_path, "session.send('Runtime.enable', {}).catch(e => {});",
            "/*session.send('Runtime.enable', {}).catch(e => {});*/")

    # patch ExecutionContext eval to still work
    frames_path = server_path + "/frames.js"

    _context_re = re.compile(r".*\s_context?\s*\(world\)\s*\{(?:[^}{]+|\{(?:[^}{]+|\{[^}{]*\})*\})*\}")
    _context_replacement = \
        " async _context(world) {\n" \
        """
        // atm ignores world_name
        if (this._isolatedContext == undefined) {
          var worldName = "utility"
          var result = await this._page._delegate._mainFrameSession._client.send('Page.createIsolatedWorld', {
            frameId: this._id,
            grantUniveralAccess: true,
            worldName: worldName
          });
          var crContext = new _crExecutionContext.CRExecutionContext(this._page._delegate._mainFrameSession._client, {id:result.executionContextId})
          this._isolatedContext = new _dom.FrameExecutionContext(crContext, this, worldName)
        }
        return this._isolatedContext
        \n""" \
        "}"
    clear_re = re.compile(
        r".\s_onClearLifecycle?\s*\(\)\s*\{")
    clear_repl = \
        " _onClearLifecycle() {\n" \
        """
        this._isolatedContext = undefined;
        """

    with open(frames_path, "r") as f:
        frames_js = f.read()
        frames_js = "// undetected-playwright-patch - custom imports\n" \
                    "var _crExecutionContext = require('./chromium/crExecutionContext')\n" \
                    "var _dom =  require('./dom')\n" \
                    + "\n" + frames_js

        # patch _context function
        frames_js = _context_re.subn(_context_replacement, frames_js, count=1)[0]
        frames_js = clear_re.subn(clear_repl, frames_js, count=1)[0]

    with open(frames_path, "w") as f:
        f.write(frames_js)


def main(build: bool = True, build_all: bool = False, ):
    cmd = "python setup.py bdist_wheel"
    if build_all:
        cmd += " --all"
    if build:
        os.system(cmd)
    else:
        rel_path = "/driver"
        module_path = pathlib.Path(os.path.dirname(playwright.__file__) + rel_path)
        patch_driver(str(module_path))
        path = pathlib.Path(os.getcwd() + "/playwright" + rel_path)
        if module_path.resolve() != path.resolve():
            patch_driver(str(path))


if __name__ == "__main__":
    main(build=True, build_all=False)

    loop = asyncio.ProactorEventLoop()
    loop.run_until_complete(patch_check_main())
