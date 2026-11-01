#!/usr/bin/env python3
"""simple3D web server.

Serves index.html (like `python3 -m http.server`) and lets the UI update
itself from GitHub without Moonraker:

  GET  /api/self/status[?fetch=1]   local/remote commit, new commits, dirty flag
  POST /api/self/update[?force=1]   git pull --ff-only (force: reset to origin)

Only fixed git commands run; nothing from the request reaches the shell.
Standard library only (Python 3.7+).
"""
import argparse
import json
import os
import subprocess
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

ROOT = os.path.dirname(os.path.abspath(__file__))
REMOTE = 'origin'
BRANCH = 'main'
RESTART_EXIT_CODE = 75   # systemd (Restart=always) starts us again
update_lock = threading.Lock()


def git(*args, timeout=60):
    """Run git in ROOT; returns (returncode, output)."""
    try:
        r = subprocess.run(['git', '-C', ROOT] + list(args),
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           universal_newlines=True, timeout=timeout)
        return r.returncode, r.stdout.strip()
    except subprocess.TimeoutExpired:
        return 124, 'git %s timed out' % args[0]
    except OSError as e:
        return 127, str(e)


def git_status(fetch):
    if git('rev-parse', '--is-inside-work-tree')[0] != 0:
        return {'error': '~/simple3D is not a git clone'}
    info = {'branch': BRANCH, 'remote': REMOTE}
    if fetch:
        code, out = git('fetch', '--quiet', REMOTE, BRANCH, timeout=90)
        if code != 0:
            info['fetch_error'] = out or 'git fetch failed'
    target = '%s/%s' % (REMOTE, BRANCH)
    info['local'] = git('rev-parse', '--short', 'HEAD')[1]
    code, remote = git('rev-parse', '--short', target)
    info['remote'] = remote if code == 0 else ''
    info['subject'] = git('log', '-1', '--format=%s', 'HEAD')[1]
    behind, ahead = 0, 0
    commits = []
    if info['remote']:
        behind = int(git('rev-list', '--count', 'HEAD..' + target)[1] or 0)
        ahead = int(git('rev-list', '--count', target + '..HEAD')[1] or 0)
        log = git('log', '--format=%h%x09%s', '-30', 'HEAD..' + target)[1]
        for line in log.splitlines():
            sha, _, subject = line.partition('\t')
            commits.append({'sha': sha, 'subject': subject})
    info['behind'] = behind
    info['ahead'] = ahead
    info['commits'] = commits
    info['dirty'] = bool(git('status', '--porcelain', '--untracked-files=no')[1])
    return info


def git_update(force):
    with update_lock:
        st = git_status(fetch=True)
        if 'error' in st:
            return 500, st
        if st.get('fetch_error'):
            return 502, {'error': st['fetch_error']}
        if st['dirty'] and not force:
            return 409, {'error': 'Local files were changed. Use Repair to reset to %s/%s.' % (REMOTE, BRANCH), 'dirty': True}
        old = git('rev-parse', 'HEAD')[1]
        target = '%s/%s' % (REMOTE, BRANCH)
        if force:
            code, out = git('reset', '--hard', target)
        else:
            code, out = git('merge', '--ff-only', target)
        if code != 0:
            return 500, {'error': out or 'git failed'}
        new = git('rev-parse', 'HEAD')[1]
        changed = git('diff', '--name-only', old, new)[1].splitlines() if old != new else []
        restart = 'server.py' in changed
        return 200, {'ok': True, 'from': old[:7], 'to': new[:7],
                     'changed': changed, 'restarting': restart, 'output': out}


class Handler(SimpleHTTPRequestHandler):
    # Python 3.9's mimetypes doesn't know the web app manifest
    extensions_map = dict(SimpleHTTPRequestHandler.extensions_map)
    extensions_map['.webmanifest'] = 'application/manifest+json'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    # --- static files: block hidden paths (.git, .gitignore, ...) ---
    def _hidden(self):
        parts = urlparse(self.path).path.split('/')
        return any(p.startswith('.') and p not in ('', '.') for p in parts)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == '/api/self/status':
            fetch = parse_qs(url.query).get('fetch', ['0'])[0] == '1'
            st = git_status(fetch)
            return self._json(500 if 'error' in st else 200, st)
        if self._hidden():
            return self.send_error(404)
        return super().do_GET()

    def do_HEAD(self):
        if self._hidden():
            return self.send_error(404)
        return super().do_HEAD()

    def do_POST(self):
        url = urlparse(self.path)
        if url.path != '/api/self/update':
            return self.send_error(404)
        force = parse_qs(url.query).get('force', ['0'])[0] == '1'
        code, body = git_update(force)
        self._json(code, body)
        if body.get('restarting'):
            # server.py itself changed: exit so systemd starts the new version
            threading.Timer(1.0, lambda: os._exit(RESTART_EXIT_CODE)).start()

    def _json(self, code, obj):
        data = json.dumps(obj).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(data)

    def end_headers(self):
        # Old iOS Safari caches hard; always revalidate the page after updates
        if urlparse(self.path).path in ('/', '/index.html'):
            self.send_header('Cache-Control', 'no-cache')
        super().end_headers()

    def log_message(self, fmt, *args):
        if '/api/' in self.path:   # keep the journal quiet; log API calls only
            sys.stderr.write('%s %s\n' % (self.address_string(), fmt % args))


def main():
    ap = argparse.ArgumentParser(description='simple3D web server')
    ap.add_argument('--port', type=int, default=8080)
    ap.add_argument('--bind', default='0.0.0.0')
    a = ap.parse_args()
    httpd = ThreadingHTTPServer((a.bind, a.port), Handler)
    print('simple3D serving %s on http://%s:%d' % (ROOT, a.bind, a.port), flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
